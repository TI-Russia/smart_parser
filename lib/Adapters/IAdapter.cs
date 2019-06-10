using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{
    public class Cell
    {
        //Gets the grid span of this cell (how many cells are merged).
        public virtual int GridSpan { get { return MergedColsCount; } }
        public virtual bool IsMerged { set; get; } = false;
        public virtual int FirstMergedRow { set; get; } = -1;
        public virtual int MergedRowsCount { set; get; } = -1;
        public virtual int MergedColsCount { set; get; } = 1;
        public virtual bool IsEmpty { set; get; } = true;
        public virtual string Text { set; get; } = "";

        public virtual string GetText(bool trim = true)
        {
            var text = Text;
            if (trim)
            {
                char[] spaces = { ' ', '\n', '\r', '\t' };
                text = text.CoalesceWhitespace().Trim(spaces);
            }

            return text;
        }
        public virtual string GetTextOneLine()
        {
            return Text.Replace("\n", " ").Trim();
        }

        public int Row { get; set; } = -1;
        public int Col { get; set; } = -1;

    };

    public class Row
    {
        public Row(IAdapter adapter, int row)
        {
            this.row = row;
            this.adapter = adapter;
            Cells = adapter.GetCells(row);
        }

        public string GetContents(DeclarationField field)
        {
            var c = adapter.GetDeclarationField(row, field);
            if (c == null)
            {
                return "";
            }
            return c.GetText(true);
        }
        public ColumnOrdering ColumnOrdering
        {
            get
            {
                return adapter.ColumnOrdering;
            }
        }

        public List<Cell> Cells { get; set; }
        IAdapter adapter;
        int row;
    }

    public class Rows
    {
        private IAdapter adapter;

        // ctor etc.

        public Row this[int index]
        {
            get
            {
                return adapter.GetRow(index);
            }
        }

        public Rows(IAdapter adapter)
        {
            this.adapter = adapter;
        }
    }


    public abstract class IAdapter
    {
        // some excel files contain 32000 columns, most of them are empty
        // we try to found real column number in the header, by default is 256
        public int MaxNotEmptyColumnsFoundInHeader = 256;
        //        Cell GetCell(string cellNum);
        abstract public Cell GetCell(int row, int column);
        public virtual List<Cell> GetCells(int row)
        {
            throw new NotImplementedException();
        }

        public Rows Rows
        {
            get
            {
                return new Rows(this);
            }
        }

        public Row GetRow(int row)
        {
            return new Row(this, row);
        }

        public bool HasDeclarationField(DeclarationField field)
        {
            return ColumnOrdering.ColumnOrder.ContainsKey(field);
        }

        public Cell GetDeclarationField(int row, DeclarationField field)
        {
            return GetCell(row, Field2Col(field));
        }

        public string GetContents(int row, DeclarationField field)
        {
            return GetDeclarationField(row, field).GetText(true);
        }


        abstract public int GetRowsCount();
        abstract public int GetColsCount();
        //abstract public int GetColsCount(int Row);


        protected int Field2Col(DeclarationField field)
        {
            int index = -1;
            if (!ColumnOrdering.ColumnOrder.TryGetValue(field, out index))
            {
                //return -1;
                throw new SystemException("Field " + field.ToString() + " not found");
            }
            return index;
        }
        public virtual int GetColsCount(int Row)
        {
            throw new NotImplementedException();
        }



        public ColumnOrdering ColumnOrdering { get; set; }
        public virtual string GetTitle()
        {
            throw new NotImplementedException();
        }

        public string DocumentFile { set; get; }

        public virtual int GetWorkSheetCount()
        {
            return 1;
        }

        public virtual void SetCurrentWorksheet(int sheetIndex)
        {
            throw new NotImplementedException();
        }

        public virtual string GetWorksheetName()
        {
            return null;
        }
        static public bool IsEmptyRow(Row r)
        {
            foreach (var cell in r.Cells)
            {
                var t = cell.GetText().Trim().Trim('\n', '\t', '\r');
                if (t != "")
                {
                    return false;
                }
            }

            return true;
        }
        public bool IsSectionRow(Row r, out string text)
        {
            text = null;
            if (r.Cells.Count == 0)
            {
                return false;
            }
            int maxMergedCols = 0;
            string rowText = "";
            int cellsWithTextCount = 0;
            foreach (var c in r.Cells)
            {
                maxMergedCols = Math.Max(c.MergedColsCount, maxMergedCols);
                if (c.Text.Trim(' ', '\n').Length > 0)
                {
                    rowText += c.Text;
                    cellsWithTextCount++;
                }
            }
            rowText = rowText.Trim(' ', '\n');
            if (cellsWithTextCount == 1) {
                // possible title, exact number of not empty columns is not yet defined
                if (maxMergedCols > 5 && rowText.Contains("Сведения о"))
                {
                    text = rowText;
                    return true;
                };
                if (rowText.Length > 10 && maxMergedCols > GetColsCount() * 0.7)
                {
                    text = rowText;
                    return true;
                }
            }
            return false;
        }
        string GetHtmlByRow(int rowIndex, string html_tag)
        {
            string result = "<tr>";
            Row row = GetRow(rowIndex);
            foreach (var c in row.Cells)
            {
                result += string.Format("<{0} colspan={1}>", html_tag, c.MergedColsCount);
                result += c.Text;
                result += string.Format("</{0}>", html_tag);
            }
            result += "</tr>";
            return result;
        }

        public string TablePortionToHtml(string Title, int header_start, int header_end, int body_start, int body_end)
        {
            string result = "<span class=\"input_title\">" + Title + "</span> <br/>";
            result += "<table class=\"input_table\">";
            for (int i=header_start;  i < header_end; i++)
            {
                result += GetHtmlByRow(i, "th");
            }
            for (int i = body_start; i < body_end; i++)
            {
                result += GetHtmlByRow(i, "td");
            }
            result += "</table>";
            return result;
        }
    }
}
