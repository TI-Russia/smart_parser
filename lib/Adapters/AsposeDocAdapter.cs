using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    class AsposeDocCell : Cell
    {
        public AsposeDocCell(Aspose.Words.Tables.Cell cell)
        {
            if (cell == null)
                return;

            String cellText = cell.ToString(Aspose.Words.SaveFormat.Text).Trim();

            Text = cellText;

            IsEmpty = String.IsNullOrEmpty(Text);

            /*
            IsEmpty = cell.Type == Aspose.Cells.CellValueType.IsNull;
            IsHeader = cell.IsMerged;
            BackgroundColor = cell.GetStyle().BackgroundColor.ToString();
            ForegroundColor = cell.GetStyle().ForegroundColor.ToString();
            Text = cell.ToString();

            IsMerged = cell.IsMerged;
            if (IsMerged)
            {
                FirstMergedRow = cell.GetMergedRange().FirstRow;
                MergedRowsCount = cell.GetMergedRange().RowCount;
            }
            */
        }
    }

    public class AsposeDocAdapter : IAdapter
    {
        public static IAdapter CreateAdapter(string fileName)
        {
            return new AsposeDocAdapter(fileName);
        }

        public override Cell GetCell(int row, int column)
        {
            Aspose.Words.Tables.Cell cell = table.Rows[row].Cells[column];
            return new AsposeDocCell(cell);
        }



        public override int GetRowsCount()
        {
            return table.Rows.Count;
        }

        public override int GetColsCount()
        {
            return table.Rows[0].Count;
        }



        private AsposeDocAdapter(string fileName)
        {
            Aspose.Words.Document doc = new Aspose.Words.Document(fileName);
            Aspose.Words.NodeCollection tables = doc.GetChildNodes(Aspose.Words.NodeType.Table, true);

            int count = tables.Count;
            if (count == 0)
            {
                throw new SystemException("No table found in document " + fileName);
            }


            table = (Aspose.Words.Tables.Table)tables[0];
        }

        private Aspose.Words.Tables.Table table;
    }
}
