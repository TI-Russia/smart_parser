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
        public AsposeExcelCell(Aspose.Cells.Cell cell, Aspose.Cells.Worksheet worksheet)
        {
            if (cell == null)
                return;
            { }

            IsEmpty = cell.Type == Aspose.Cells.CellValueType.IsNull;
            // nobody wants to know how excel represents numbers inside itself
            // for "size_raw"
            Text = cell.GetStringValue(Aspose.Cells.CellValueFormatStrategy.DisplayStyle);

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
                MergedRowsCount = 1;
                FirstMergedRow = cell.Row;
            }
            Row = cell.Row;
            Col = cell.Column;
            CellWidth = 0;
            for (int i = 0; i < MergedColsCount;i++)
            {
                //test File17207: GetColumnWidthPixel returns 45, GetColumnWidth returns 0 for the same cell 
                CellWidth += (int)worksheet.Cells.GetColumnWidthPixel(cell.Column + i);
            }
        }
    }
    public class AsposeExcelAdapter : IAdapter
    {
        public override bool IsExcel() { return true; }

        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess = -1)
        {
            return new AsposeExcelAdapter(fileName, maxRowsToProcess);
        }

        public override string GetDocumentPosition(int row, int col)
        {
            return GetDocumentPositionExcel(row, col);
        }


        public override Cell GetCell(int row, int column)
        {
            Aspose.Cells.Cell cell = worksheet.Cells.GetCell(row, column);
            return new AsposeExcelCell(cell, worksheet);
        }

        public override int GetRowsCount()
        {
            if (MaxRowsToProcess != -1)
            {
                return Math.Min(MaxRowsToProcess, WorkSheetRows);
            }
            return WorkSheetRows;
        }

        public override int GetColsCount()
        {
            return totalColumns;
        }

        public override List<Cell> GetCells(int rowIndex, int maxColEnd = IAdapter.MaxColumnsCount)
        {
            List<Cell> result = new List<Cell>();
            Aspose.Cells.Row row = worksheet.Cells.Rows[rowIndex];
            Aspose.Cells.Cell firstCell = row.FirstCell;
            Aspose.Cells.Cell lastCell = row.LastCell;
            if (lastCell == null)
                return result;

            for (int i = 0; i <= lastCell.Column; i++)
            {
                if (i >= maxColEnd)
                {
                    break;
                }
                Aspose.Cells.Cell cell = row.GetCellOrNull(i);
                result.Add(new AsposeExcelCell(cell, worksheet));
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

        public override string GetTitleOutsideTheTable()
        {
            return "";
        }


        private AsposeExcelAdapter(string fileName, int maxRowsToProcess)
        {
            MaxRowsToProcess = maxRowsToProcess;
            DocumentFile = fileName;
            workbook = new Aspose.Cells.Workbook(fileName);
            // if there are multiple worksheets it is a problem
            // generate exception if more then one non-hidden worksheet
            //worksheet = workbook.Worksheets[0];
            int wsCount = 0;
            worksheet = null;
            int max_rows_count = 0;
            foreach (var ws in workbook.Worksheets)
            {
                if (ws.IsVisible && ws.Cells.Rows.Count > 0)
                {
                    wsCount++;
                    if (worksheet == null || max_rows_count < ws.Cells.Rows.Count)
                    {
                        worksheet = ws;
                        max_rows_count = ws.Cells.Rows.Count;
                    }
                }
            }
            if (wsCount == 0)
            {
                throw new Exception(String.Format("Excel sheet {0} has no visible worksheets", fileName));
            }
            workSheetName = worksheet.Name;

            worksheetCount = wsCount;
            WorkSheetRows = worksheet.Cells.Rows.Count;
            totalColumns = worksheet.Cells.MaxColumn + 1;

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
            WorkSheetRows = worksheet.Cells.Rows.Count;
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
        private int WorkSheetRows;
        private int totalColumns;
        private int worksheetCount;
        private string workSheetName;
        private int MaxRowsToProcess;

    }
}
