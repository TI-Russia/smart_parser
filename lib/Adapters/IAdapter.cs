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
using Smart.Parser.Lib.Adapters.DocxSchemes;

namespace Smart.Parser.Adapters
{
    public abstract class IAdapter : TSectionPredicates
    {
        // some excel files contain 32000 columns, most of them are empty
        // we try to found real column number in the header, by default is 1024
        public const int MaxColumnsCount = 1024;

        // specific scheme to parse tables
        public IAdapterScheme CurrentScheme = null;

        public static string ConvertedFileStorageUrl = "";

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
        public virtual List<Cell> GetCells(int row, int maxColEnd=MaxColumnsCount)
        {
            throw new NotImplementedException();
        }

        public DataRow GetRow(ColumnOrdering columnOrdering, int row)
        {
            return new DataRow(this, columnOrdering, row);
        }

        public static bool IsNumbersRow(List<Cell> cells) { 
            return String.Join(" ", cells.Select(c => c.Text.RemoveCharacters('\n', ' ')))
            .StartsWith("1 2 3 4");
        }

        // напрямую используется, пока ColumnOrdering еще не построен
        // во всех остальных случаях надо использовать Row.GetDeclarationField
        virtual public Cell GetDeclarationFieldWeak(ColumnOrdering columnOrdering, int row, DeclarationField field, out TColumnInfo colSpan)
        {
            if (!columnOrdering.ColumnOrder.TryGetValue(field, out colSpan))
            {
                throw new SmartParserFieldNotFoundException(String.Format("Field {0} not found, row={1}", field.ToString(), row));
            }

            var exactCell = GetCell(row, colSpan.BeginColumn);
            if (exactCell == null)
            {
                var rowData = GetCells(row);
                throw new SmartParserFieldNotFoundException(String.Format("Field {0} not found, row={1}, col={2}. Row.Cells.Count = {3}",
                    field.ToString(),
                    row,
                    colSpan.BeginColumn,
                    rowData.Count
                    ));
            }
            return exactCell;
        }


        abstract public int GetRowsCount();
        abstract public int GetColsCount();


        public virtual string GetTitleOutsideTheTable()
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
        public virtual string GetDocumentDepartmentFromMetaTag()
        {
            return null;
        }
        public virtual string GetDocumentUrlFromMetaTag()
        {
            return null;
        }

        public int GetUnmergedColumnsCountByFirstRow()
        {
            if (GetRowsCount() == 0) return -1;
            int sum = 0;
            foreach (var c in GetCells(0))
            {
                sum += c.MergedColsCount;
            }
            return sum;
        }

        public static int FindMergedCellByColumnNo<T>(List<List<T>> tableRows, int row, int column) where T : Cell
        {
            List<T> r = tableRows[row];
            int sumspan = 0;
            for (var i = 0; i < r.Count; ++i)
            {
                int span = r[i].MergedColsCount;
                if ((column >= sumspan) && (column < sumspan + span))
                    return i;
                sumspan += span;
            }
            return -1;
        }
        protected static List<List<T>> DropDayOfWeekRows<T>(List<List<T>> tableRows) where T : Cell
        {
            List<string> daysOfWeek = new List<string> { "пн", "вт", "ср", "чт", "пт", "сб", "вс" };
            return  tableRows.TakeWhile(x => !x.All(y => daysOfWeek.Contains(y.Text.ToLower().Trim()))).ToList();
        }

        protected static bool CheckNameColumnIsEmpty<T>(List<List<T>> tableRows, int start) where T : Cell
        {
            if (tableRows.Count - start < 3)
                return false; // header only

            var nameInd = tableRows[start].FindIndex(x => x.Text.Length < 100 && x.Text.IsName());
            if (nameInd == -1) return false;
            for (int i = start + 1; i < tableRows.Count; ++i)
            {
                if (nameInd < tableRows[i].Count && !tableRows[i][nameInd].IsEmpty)
                {
                    return false;
                }
            }
            return true;
        }

        protected static void MergeRow<T>(List<T> row1, List<T> row2) where T : Cell
        {
            for (int i = 0; i < row1.Count; ++i)
            {
                row1[i].Text += "\n" + row2[i].Text;
            }
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
                if (c.FirstMergedRow != rowIndex)
                {
                    continue;
                }
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
                if (IsSectionRow(row, columnOrdering.GetMaxColumnEndIndex(), false, out dummy))
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
                file.WriteLine("<html><table border=1>");
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


        public virtual int? GetWorksheetIndex()
        {
            return null;
        }


        
    }
}
