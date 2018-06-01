using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

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
            IsEmpty = cell.Type == Aspose.Cells.CellValueType.IsNull;
            IsHeader = cell.IsMerged;
            BackgroundColor = cell.GetStyle().BackgroundColor.ToString();
            ForegroundColor = cell.GetStyle().ForegroundColor.ToString();
            Text = cell.ToString();
        }
    }
    public class AsposeExcelAdapter : IAdapter
    {
        public static IAdapter CreateAsposeExcelAdapter(string fileName)
        {
            return new AsposeExcelAdapter(fileName);
        }

        Cell IAdapter.GetCell(string cellNum)
        {
            Aspose.Cells.Cell cell = worksheet.Cells[cellNum];

            return new AsposeExcelCell(cell);
        }
        Cell IAdapter.GetCell(int row, int column)
        {
            Aspose.Cells.Cell cell = worksheet.Cells.GetCell(row, column);
            return new AsposeExcelCell(cell);
        }

        int IAdapter.GetRowsCount()
        {
            return worksheet.Cells.Rows.Count;
        }
        private AsposeExcelAdapter(string fileName)
        {
            Aspose.Cells.Workbook workbook = new Aspose.Cells.Workbook(fileName);
            worksheet = workbook.Worksheets[0];
        }

        private Aspose.Cells.Worksheet worksheet;
    }
}
