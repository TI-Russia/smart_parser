using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using CsvHelper;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;
using Parser.Lib;

namespace Smart.Parser.Adapters
{
    public abstract class IAdapter : TSectionPredicates
    {
        // some excel files contain 32000 columns, most of them are empty
        // we try to found real column number in the header, by default is 256
        static private readonly int MaxColumnsCount = 256;
        public int MaxNotEmptyColumnsFoundInHeader = MaxColumnsCount;

        public void RestartAdapterForExcelSheet()
        {
            MaxNotEmptyColumnsFoundInHeader = MaxColumnsCount;
        }
        public virtual bool IsExcel() { return false; }
        public virtual string GetDocumentPosition(int row, int col)
        {
            return null;
        }
        public string GetDocumentPositionExcel(int row, int col)
        {
            return "R" + (row + 1).ToString() + "C" + (col + 1).ToString();
        }

        
        abstract public Cell GetCell(int row, int column);
        public virtual List<Cell> GetCells(int row)
        {
            throw new NotImplementedException();
        }

        public DataRow GetRow(ColumnOrdering columnOrdering, int row)
        {
            return new DataRow(this, columnOrdering, row);
        }


        // используется, пока ColumnOrdering еще не построен
        // во всех остальных случаях надо использовать Row.GetDeclarationField
        virtual public Cell GetDeclarationFieldWeak(ColumnOrdering columnOrdering, int row, DeclarationField field)
        {
            TColumnInfo colSpan;
            if (!columnOrdering.ColumnOrder.TryGetValue(field, out colSpan))
            {
                throw new SystemException(String.Format("Field {0} not found, row={1}", field.ToString(), row));
            }

            var exactCell = GetCell(row, colSpan.BeginColumn);
            if (exactCell == null)
            {
                throw new SystemException(String.Format("Field {0} not found, row={1}, col={2}", field.ToString(), row, colSpan.BeginColumn));
            }

            if (exactCell.Text.Trim() != "")
            {
                return exactCell;
            }
            for (int i = exactCell.Col + exactCell.MergedColsCount; i < colSpan.EndColumn;)
            {
                var mergedCell = GetCell(row, i);
                if (mergedCell == null)
                {
                    break;
                }
                if (mergedCell.Text.Trim() != "")
                {
                    return mergedCell;
                }
                i += mergedCell.MergedColsCount;
            }
            return exactCell;
        }


        abstract public int GetRowsCount();
        abstract public int GetColsCount();


        public virtual int GetColsCount(int Row)
        {
            throw new NotImplementedException();
        }

        public virtual string GetTitle()
        {
            throw new NotImplementedException();
        }

        public string DocumentFile { set; get; }

        public virtual int GetWorkSheetCount()
        {
            return 1;
        }
        public virtual int GetTablesCount()
        {
            return GetWorkSheetCount();
        }

        public virtual void SetCurrentWorksheet(int sheetIndex)
        {
            throw new NotImplementedException();
        }

        public virtual string GetWorksheetName()
        {
            return null;
        }
        public bool IsEmptyRow(int rowIndex)
        {
            foreach (var cell in GetCells(rowIndex))
            {
                if (!cell.IsEmpty) return false;
            }
            return true;
        }
        public bool IsSectionRow(List<Cell> cells, bool prevRowIsSection, out string text)
        {
            return IAdapter.IsSectionRow(cells, prevRowIsSection, GetColsCount(), out text);
        }
        

        public class TJsonCell
        {
            public int mc;
            public int mr;
            public int r;
            public int c;
            public string t;
        }
        public class TJsonTablePortion
        {
            public string Title;
            public string InputFileName;
            public int DataStart;
            public int DataEnd;
            public List<List<TJsonCell>> Header = new List<List<TJsonCell>>();
            public List<List<TJsonCell>> Section = new List<List<TJsonCell>>();
            public List<List<TJsonCell>> Data = new List<List<TJsonCell>>();
        }
        List<TJsonCell> GetJsonByRow(List<Cell> row)
        {
            var outputList = new List<TJsonCell>();
            foreach (var c in row)
            {
                var jc = new TJsonCell();
                jc.mc = c.MergedColsCount;
                jc.mr = c.MergedRowsCount;
                jc.r = c.Row;
                jc.c = c.Col;
                jc.t = c.Text;
                outputList.Add(jc);
            }
            return outputList;
        }
        string GetHtmlByRow(List<Cell> row, int rowIndex)
        {
            string res = string.Format("<tr rowindex={0}>\n", rowIndex);
            foreach (var c in row)
            {
                res += "\t<td";
                if (c.MergedColsCount > 1)
                {
                    res += string.Format(" colspan={0}", c.MergedColsCount);
                }
                if (c.MergedRowsCount > 1)
                {
                    res += string.Format(" rowspan={0}", c.MergedRowsCount);
                }
                string text = c.Text.Replace("\n", "<br/>");
                res += ">" + text + "</td>\n";
            }
            res += "</tr>\n";
            return res;
        }

        public TJsonTablePortion TablePortionToJson(ColumnOrdering columnOrdering, int body_start, int body_end)
        {
            var table = new TJsonTablePortion();
            table.DataStart = body_start;
            int headerEnd = columnOrdering.GetPossibleHeaderEnd();
            for (int i= columnOrdering.GetPossibleHeaderBegin();  i < columnOrdering.GetPossibleHeaderEnd(); i++)
            {
                var row = GetJsonByRow(GetCells(i));
                table.Header.Add(row);
            }

            // find section before data
            for (int i = body_start; i >= headerEnd; i--)
            {
                string dummy;
                // cannot use prevRowIsSection
                var row = GetCells(i);
                if (IsSectionRow(row, false, out dummy))
                {
                    table.Section.Add(GetJsonByRow(row));
                    break;
                }
            }
            
            int maxRowsCount = body_end - body_start;
            table.DataEnd = body_start;
            int addedRows = 0;
            while (table.DataEnd < GetRowsCount() && addedRows < maxRowsCount)
            {
                if (!IsEmptyRow(table.DataEnd))
                {
                    table.Data.Add(GetJsonByRow(GetCells(table.DataEnd)));
                    addedRows++;
                }
                table.DataEnd++;
            }
            return table;
        }

        public void WriteHtmlFile( string htmlFileName)
        {
            using (System.IO.StreamWriter file = new System.IO.StreamWriter(htmlFileName))
            {
                file.WriteLine("<html><table>");
                for (int i = 0; i < GetRowsCount(); i++)
                {
                    file.WriteLine(GetHtmlByRow(GetCells(i), i));
                }
                file.WriteLine("</table></html>");
            }
        }


        public void ExportCSV(string csvFile)
        {
            int rowCount = GetRowsCount();
            int colCount = GetColsCount();

            var stream = new FileStream(csvFile, FileMode.Create);
            var writer = new StreamWriter(stream) { AutoFlush = true };

            var csv = new CsvWriter(writer);

            for (int r = 0; r < rowCount; r++)
            {
                for (int c = 0; c < colCount; c++)
                {
                    string value = GetCell(r, c).Text;
                    csv.WriteField(value);
                }
                csv.NextRecord();
            }
            csv.Flush();
        }

        public void SetMaxColumnsCountByHeader(int headerRowCount)
        {
            int maxfound = 0;
            for (int row = 0; row < headerRowCount; ++row)
            {
                for (int col = 0; col < 256; ++col)
                {
                    var c = GetCell(row, col);
                    if (c == null)
                    {
                        break;
                    }
                    if (c.GetText() != "")
                    {
                        maxfound = Math.Max(col, maxfound);
                    }
                }
            }
            MaxNotEmptyColumnsFoundInHeader = maxfound;
            Logger.Debug($"Set MaxNotEmptyColumnsFoundInHeader to {maxfound}");
        }



        public virtual int? GetWorksheetIndex()
        {
            return null;
        }

        public static string ConvertedFileDir { set; get; } = null;

    }
}
