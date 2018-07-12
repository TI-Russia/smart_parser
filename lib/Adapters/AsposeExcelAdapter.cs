using System;
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
            }
        }
    }
    public class AsposeExcelAdapter : AdapterBase, IAdapter
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

        public Cell GetDeclarationField(int row, DeclarationField field)
        {
            return GetCell(row, Field2Col(field));
        }

        public Cell GetCell(int row, int column)
        {
            Aspose.Cells.Cell cell = worksheet.Cells.GetCell(row, column);
            return new AsposeExcelCell(cell);
        }

        public int GetRowsCount()
        {
            return totalRows;
        }

        public int GetColsCount()
        {
            return totalColumns;
        }

        private AsposeExcelAdapter(string fileName)
        {
            Aspose.Cells.Workbook workbook = new Aspose.Cells.Workbook(fileName);
            worksheet = workbook.Worksheets[0];
            totalRows = worksheet.Cells.Rows.Count;
            totalColumns = worksheet.Cells.MaxColumn + 1;
        }

        private Aspose.Cells.Worksheet worksheet;
        private int totalRows;
        private int totalColumns;
    }
}
