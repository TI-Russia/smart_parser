using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

using NPOI.SS.UserModel;
using NPOI.SS.Util;
using NPOI.XSSF.UserModel;
using Microsoft.Office.Interop.Excel;

using TI.Declarator.ParserCommon;
using Parser.Lib;

namespace Smart.Parser.Adapters
{

    public class NpoiExcelAdapter : IAdapter
    {
        private XSSFWorkbook WorkBook;
        private Cell EmptyCell;
        private int MaxRowsToProcess;
        private string TempFileName;
        string ConvertFile2TempXlsX(string filename)
        {
            Application excel = new Application();
            var doc = excel.Workbooks.Open(Path.GetFullPath(filename),ReadOnly:true);
            TempFileName = Path.GetTempFileName();
            Logger.Debug(string.Format("use {0} to store temp xlsx file", TempFileName));
            excel.DisplayAlerts = false;
            doc.SaveAs(
                Filename:TempFileName,
                FileFormat: XlFileFormat.xlOpenXMLWorkbook,
                ConflictResolution: XlSaveConflictResolution.xlLocalSessionChanges,
                WriteResPassword: "");
            doc.Close();
            excel.Quit();
            excel = null;
            return TempFileName;
        }

        public NpoiExcelAdapter(string fileName, int maxRowsToProcess = -1)
        {
            DocumentFile = fileName;
            TempFileName = null;
            string extension = Path.GetExtension(fileName);
            if (extension == ".xls")
            {
                fileName = ConvertFile2TempXlsX(fileName);
            }
            StreamReader file = new StreamReader(Path.GetFullPath(fileName));
            WorkBook = new XSSFWorkbook(file.BaseStream);
            //WorkBook = new XSSFWorkbook(Path.GetFullPath(fileName));
            EmptyCell = new Cell();
            MaxRowsToProcess = maxRowsToProcess;
            TrimEmptyLines();
        }

        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess = -1)
        {
            return new NpoiExcelAdapter(fileName, maxRowsToProcess);
        }

        ~NpoiExcelAdapter()
        {
            WorkBook = null;
            if (TempFileName != null) File.Delete(TempFileName);
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

                index += cell.MergedColsCount;
                if (index >= MaxNotEmptyColumnsFoundInHeader)
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

            var cellContents = cell.ToString();
            return new Cell
            {
                IsMerged = isMergedCell,
                FirstMergedRow = firstMergedRow,
                MergedRowsCount = mergedRowsCount,
                MergedColsCount = mergedColsCount,
                // FIXME to init this property we need a formal definition of "header cell"
                IsEmpty = cellContents.IsNullOrWhiteSpace(),
                Text = cellContents,
                Row = row,
                Col = column,
            };
        }

        void TrimEmptyLines()
        {
            int row = GetRowsCount() - 1; 
            while (row >= 0 && IsEmptyRow(row)) {
                MaxRowsToProcess = row;
                row--;
            }
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
