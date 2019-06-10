using Parser.Lib;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    class AsposeExcelCell : Cell
    {
        public AsposeExcelCell(Aspose.Cells.Cell cell)
        {
            if (cell == null)
                return;
            { }

            IsEmpty = cell.Type == Aspose.Cells.CellValueType.IsNull;
            Text = cell.GetStringValue(Aspose.Cells.CellValueFormatStrategy.None);

            IsMerged = cell.IsMerged;
            if (IsMerged)
            {
                FirstMergedRow = cell.GetMergedRange().FirstRow;
                MergedRowsCount = cell.GetMergedRange().RowCount;
                MergedColsCount = cell.GetMergedRange().ColumnCount;
            }
            else
            {
                MergedColsCount = 1;
            }
            Row = cell.Row;
            Col = cell.Column;
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

        public override List<Cell> GetCells(int rowIndex)
        {
            List<Cell> result = new List<Cell>();
            Aspose.Cells.Row row = worksheet.Cells.Rows[rowIndex];
            Aspose.Cells.Cell firstCell = row.FirstCell;
            Aspose.Cells.Cell lastCell = row.LastCell;
            if (lastCell == null)
                return result;

            for (int i = 0; i <= lastCell.Column; i++)
            {
                Aspose.Cells.Cell cell = row.GetCellOrNull(i);
                result.Add(new AsposeExcelCell(cell));
                if (cell != null && cell.IsMerged && cell.GetMergedRange().ColumnCount > 1)
                {
                    i += cell.GetMergedRange().ColumnCount - 1;
                }
            }
            /*
            IEnumerator enumerator = worksheet.Cells.Rows[rowIndex].GetEnumerator();
            int range_end = -1;
            while (enumerator.MoveNext())
            {
                Aspose.Cells.Cell cell = (Aspose.Cells.Cell)enumerator.Current;
                if (cell.Column < range_end)
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
            */
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
            DocumentFile = fileName;
            workbook = new Aspose.Cells.Workbook(fileName);
            // if there are multiple worksheets it is a problem
            // generate exception if more then one non-hidden worksheet
            //worksheet = workbook.Worksheets[0];
            int wsCount = 0;
            worksheet = null;
            foreach (var ws in workbook.Worksheets)
            {
                if (ws.IsVisible && ws.Cells.Rows.Count > 0)
                {
                    wsCount++;
                    if (worksheet == null)
                    {
                        worksheet = ws;
                    }
                }
            }
            if (wsCount == 0)
            {
                throw new Exception(String.Format("Excel sheet {0} has no visible worksheets", fileName));
            }
            workSheetName = worksheet.Name;

            worksheetCount = wsCount;
            totalRows = worksheet.Cells.Rows.Count;
            totalColumns = worksheet.Cells.MaxColumn + 1;

            FindTitle();
        }

        public override void SetCurrentWorksheet(int sheetIndex)
        {
            int count = 0;
            worksheet = null;
            foreach (var ws in workbook.Worksheets)
            {
                if (ws.IsVisible && ws.Cells.Rows.Count > 0)
                {
                    if (count == sheetIndex)
                    {
                        worksheet = ws;
                        break;
                    }
                    count++;
                }
            }
            if (worksheet == null)
            {
                throw new SmartParserException("wrong  sheet index");
            }
            workSheetName = worksheet.Name;
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
        public override int GetWorkSheetCount()
        {
            return worksheetCount;
        }

        public override string GetWorksheetName()
        {
            return workSheetName;
        }

        public override int? GetWorksheetIndex()
        {
            return worksheet.Index;
        }


        private Aspose.Cells.Workbook workbook;
        private Aspose.Cells.Worksheet worksheet;
        private int totalRows;
        private int totalColumns;
        private string title;
        private int worksheetCount;
        private string workSheetName;
    }
}
