using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

using NPOI.SS.UserModel;
using NPOI.SS.Util;
using NPOI.XSSF.UserModel;

using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    public class NpoiExcelAdapter : IAdapter
    {
        private XSSFWorkbook WorkBook;
        private Cell EmptyCell;
        private int MaxRowsToProcess;
        int MaxColumnsToProcess = 32;

        public NpoiExcelAdapter(string filename, int maxRowsToProcess = -1)
        {
            WorkBook = new XSSFWorkbook(Path.GetFullPath(filename));
            EmptyCell = new Cell();
            MaxRowsToProcess = maxRowsToProcess;
        }
        
        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess = -1)
        {
            return new NpoiExcelAdapter(fileName, maxRowsToProcess);
        }
        
        public Cell GetCell(string cellIndex)
        {
            CellReference cellRef = new CellReference(cellIndex);
            return GetCell(cellRef.Row, cellRef.Col);
        }

        public override List<Cell> GetCells(int row)
        {
            ISheet defaultSheet = WorkBook.GetSheetAt(0);
            int index = 0;
            List<Cell> result = new List<Cell>();
            while (true)
            {
                var cell = GetCell(row, index);

                if (cell == EmptyCell) break;
                result.Add(cell);

                if (cell.IsMerged)
                {
                    int count = cell.MergedColsCount;
                    index += count;
                }
                else
                {
                    index++;
                }
                if (index > MaxNotEmptyColumnsFoundInHeader)
                {
                    break;
                }
            }

            return result;
        }
        public class CellAddress
        {
            public int row { get; set; }
            public int column { get; set; }
            public override int GetHashCode()
            {
                return row*100 + column; //maximal 100 columns in excel 
            }
            public override bool Equals(object obj)
            {
                return Equals(obj as CellAddress);
            }
            public bool Equals(CellAddress obj)
            {
                return obj != null && obj.row == this.row && obj.column == this.column;
            }
        }
        Dictionary<CellAddress, Cell> Cache = new Dictionary<CellAddress, Cell>();
        public override Cell GetCell(int row, int column)
        {
            var address = new CellAddress{row=row, column=column};
            if (Cache.ContainsKey(address))
            {
                return Cache[address];
            }
            var c = GetCellWithoutCache(row, column);
            Cache[address] = c;
            return c;
        }
        Cell GetCellWithoutCache(int row, int column)
        {
            ISheet defaultSheet = WorkBook.GetSheetAt(0);
            var currentRow = defaultSheet.GetRow(row);
            if (currentRow == null)
            {
                //null if row contains only empty cells
                return EmptyCell;
            }
            ICell cell = currentRow.GetCell(column);
            if (cell == null) return EmptyCell;
            
            bool isMergedCell = cell.IsMergedCell;
            int firstMergedRow;
            int mergedRowsCount;
            int mergedColsCount;
            if (isMergedCell)
            {
                CellRangeAddress mergedRegion = GetMergedRegion(defaultSheet, cell);
                firstMergedRow = mergedRegion.FirstRow;
                mergedRowsCount = mergedRegion.LastRow - mergedRegion.FirstRow + 1;
                mergedColsCount = mergedRegion.LastColumn - mergedRegion.FirstColumn + 1;
            }
            else
            {
                firstMergedRow = cell.RowIndex;
                mergedRowsCount = 1;
                mergedColsCount = 1;
                
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

            var cellContents = cell.ToString();
            return new Cell
            {
                IsMerged = isMergedCell,
                FirstMergedRow = firstMergedRow,
                MergedRowsCount = mergedRowsCount,
                MergedColsCount = mergedColsCount,
                // FIXME to init this property we need a formal definition of "header cell"
                IsHeader = false,
                IsEmpty = cellContents.IsNullOrWhiteSpace(),
                BackgroundColor = backgroundColor,
                ForegroundColor = foregroundColor,
                Text = cellContents,
                Row = row,
                Col = column,
            };
        }


        public override int GetRowsCount()
        {
            int rowCount = WorkBook.GetSheetAt(0).PhysicalNumberOfRows;
            if (MaxRowsToProcess != -1)
            {
                return Math.Min(MaxRowsToProcess, rowCount);
            }
            return rowCount;
        }

        public override int GetColsCount()
        {
            return Math.Min(MaxNotEmptyColumnsFoundInHeader, WorkBook.GetSheetAt(0).GetRow(0).Cells.Count);
        }

        public override int GetColsCount(int row)
        {
            return GetCells(row).Count();
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
