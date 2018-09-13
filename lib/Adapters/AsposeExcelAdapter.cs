using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    /*
        public virtual bool IsHeader { set; get; }
        public virtual bool IsEmpty { set; get; }
        public virtual string BackgroundColor { set; get; }
        public virtual string ForegroundColor { set; get; }

        public virtual string Text { set; get; }
     */

    class AsposeExcelCell : Cell
    {
        public AsposeExcelCell(Aspose.Cells.Cell cell)
        {
            if (cell == null)
                return;
            { }

            IsEmpty = cell.Type == Aspose.Cells.CellValueType.IsNull;
            IsHeader = cell.IsMerged;
            BackgroundColor = cell.GetStyle().BackgroundColor.ToString();
            ForegroundColor = cell.GetStyle().ForegroundColor.ToString();
            Text = cell.GetStringValue(Aspose.Cells.CellValueFormatStrategy.None);

            IsMerged = cell.IsMerged;
            if (IsMerged)
            {
                FirstMergedRow = cell.GetMergedRange().FirstRow;
                MergedRowsCount = cell.GetMergedRange().RowCount;
                MergedColsCount = cell.GetMergedRange().ColumnCount;
            }
        }
    }
    public class AsposeExcelAdapter : IAdapter
    {
        public static IAdapter CreateAdapter(string fileName)
        {
            return new AsposeExcelAdapter(fileName);
        }

        //Cell IAdapter.GetCell(string cellNum)
        //{
        //    Aspose.Cells.Cell cell = worksheet.Cells[cellNum];
        //
        //    return new AsposeExcelCell(cell);
        //}
        //Cell IAdapter.GetCell(int row, int column)
        //{
        //    return this.GetCell(row, column);
        //}


        public override Cell GetCell(int row, int column)
        {
            Aspose.Cells.Cell cell = worksheet.Cells.GetCell(row, column);
            return new AsposeExcelCell(cell);
        }

        public override int GetRowsCount()
        {
            return totalRows;
        }

        public override int GetColsCount()
        {
            return totalColumns;
        }

        public override List<Cell> GetCells(int row)
        {
            int index = 0;
            List<Cell> result = new List<Cell>();
            IEnumerator enumerator = worksheet.Cells.Rows[row].GetEnumerator();
            int range_end = -1;
            while (enumerator.MoveNext())
            {
                Aspose.Cells.Cell cell = (Aspose.Cells.Cell)enumerator.Current;
                if (index < range_end)
                {
                    index++;
                    continue;
                }

                result.Add(new AsposeExcelCell(cell));

                if (cell.IsMerged)
                {
                    int first = cell.GetMergedRange().FirstColumn;
                    int count = cell.GetMergedRange().ColumnCount;
                    range_end = first + count;
                }
                index++;
            }
            return result;
        }

        public override int GetColsCount(int row)
        {
            return GetCells(row).Count();
        }
        public override string GetTitle()
        {
            return title;
        }


        private AsposeExcelAdapter(string fileName)
        {
            Aspose.Cells.Workbook workbook = new Aspose.Cells.Workbook(fileName);
            worksheet = workbook.Worksheets[0];
            totalRows = worksheet.Cells.Rows.Count;
            totalColumns = worksheet.Cells.MaxColumn + 1;

            FindTitle();
        }

        private void FindTitle()
        {
            int row = 0;
            string text = "";
            while (row < GetRowsCount())
            {
                Cell cell = GetCell(row, 0);
                if (cell.IsMerged && cell.MergedColsCount > 3)
                {
                    text += cell.Text;
                    row += cell.MergedRowsCount;
                }
                else
                    break;
            }

            title = text;
        }

        private Aspose.Cells.Worksheet worksheet;
        private int totalRows;
        private int totalColumns;
        private string title;
    }
}
