using System;
using System.Linq;

using NPOI.SS.UserModel;
using NPOI.SS.Util;
using NPOI.XSSF.UserModel;

using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;

namespace TI.Declarator.ExcelParser
{
    class XlsxAdapter : IAdapter
    {
        private XSSFWorkbook WorkBook;
        public XlsxAdapter(string filename)
        {
            WorkBook = new XSSFWorkbook(filename);
        }

        public Cell GetCell(string cellIndex)
        {
            CellReference cellRef = new CellReference(cellIndex);
            return GetCell(cellRef.Row, cellRef.Col);
        }

        public override Cell GetCell(int row, int column)
        {
            ISheet defaultSheet = WorkBook.GetSheetAt(0);
            ICell cell = defaultSheet.GetRow(row).GetCell(column);

            if (cell == null) return null;

            string cellContents;
            bool isMergedCell = cell.IsMergedCell;
            int firstMergedRow;
            int mergedRowsCount;
            if (isMergedCell)
            {
                CellRangeAddress mergedRegion = GetMergedRegion(defaultSheet, cell);

                firstMergedRow = mergedRegion.FirstRow;
                mergedRowsCount = mergedRegion.LastRow - mergedRegion.FirstRow + 1;
                cellContents = defaultSheet.GetRow(mergedRegion.FirstRow)
                                           .GetCell(mergedRegion.FirstColumn)
                                           .ToString();
            }
            else
            {
                firstMergedRow = cell.RowIndex;
                mergedRowsCount = 1;
                cellContents = cell.ToString();
            }

            string backgroundColor;
            if (cell.CellStyle.FillBackgroundColorColor?.RGB == null)
            {
                backgroundColor = null;
            }
            else
            {
                backgroundColor = cell.CellStyle.FillBackgroundColorColor.RGB.Select(v => v.ToString("X2"))
                                                                             .Aggregate("", (str1, str2) => str1 + str2);
            }

            string foregroundColor;
            if (cell.CellStyle.FillForegroundColorColor?.RGB == null)
            {
                foregroundColor = null;
            }
            else
            {
                foregroundColor = cell.CellStyle.FillForegroundColorColor.RGB.Select(v => v.ToString("X2"))
                                                                             .Aggregate("", (str1, str2) => str1 + str2);
            }


            return new Cell
            {
                IsMerged = isMergedCell,
                FirstMergedRow = firstMergedRow,
                MergedRowsCount = mergedRowsCount,
                // FIXME to init this property we need a formal definition of "header cell"
                IsHeader = false,
                IsEmpty = cellContents.IsNullOrWhiteSpace(),
                BackgroundColor = backgroundColor,
                ForegroundColor = foregroundColor,
                Text = cellContents,
            };
        }


        public override int GetRowsCount()
        {
            ISheet defaultSheet = WorkBook.GetSheetAt(0);
            int numRows = defaultSheet.LastRowNum;
            // since LastRowNum returns zero-based row index
            // we need an extra check to determine if the sheet has 0 or 1 rows
            if (numRows == 0 && defaultSheet.PhysicalNumberOfRows == 0)
            {
                return 0;
            }
            else
            {
                return numRows + 1;
            }
        }

        public override int GetColsCount()
        {
            throw new NotImplementedException();
        }


        private CellRangeAddress GetMergedRegion(ISheet sheet, ICell cell)
        {
            for (int i = 0; i < sheet.NumMergedRegions; i++)
            {
                var region = sheet.GetMergedRegion(i);
                if ((region.FirstRow <= cell.RowIndex && cell.RowIndex <= region.LastRow) &&
                    (region.FirstColumn <= cell.ColumnIndex && cell.ColumnIndex <= region.LastColumn))
                {
                    return region;
                }
            }

            throw new Exception($"Could not find merged region containing cell at row#{cell.RowIndex}, column#{cell.ColumnIndex}");
        }
    }
}
