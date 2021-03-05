using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
#if WIN64
using Excel = Microsoft.Office.Interop.Excel;

using TI.Declarator.ParserCommon;
namespace Smart.Parser.Adapters
{
    class MSExcelCell : Cell
    {
        public MSExcelCell(Excel.Range range, int width)
        {
            if (range == null || range.Count == 0)
                return;
            { }
            IsEmpty = range.Text.IsNullOrWhiteSpace();
            Text = range.Text;
            IsMerged = range.MergeCells;
            if (IsMerged)
            {
                FirstMergedRow = range.MergeArea.Row;
                MergedRowsCount = range.MergeArea.Rows.Count;
                MergedColsCount = range.MergeArea.Columns.Count;
            }
            Row = range.Row - 1;
            Col = range.Column - 1;
            CellWidth = width;
        }

    }

    public class MicrosoftExcelAdapter : IAdapter
    {
        private int MaxRowsToProcess;
        private Excel.Workbook WorkBook = null;
        private Excel.Worksheet WorkSheet = null;
        private int TotalRows;
        private int TotalColumns;
        private Microsoft.Office.Interop.Excel.Application ExcelApplication;
        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess=-1)
        {
            return new MicrosoftExcelAdapter(fileName, maxRowsToProcess);
        }

        public override bool IsExcel() { return true; }

        public MicrosoftExcelAdapter(string filename, int maxRowsToProcess=-1)
        {
            MaxRowsToProcess = maxRowsToProcess;
            ExcelApplication = new Excel.Application();
            WorkBook = ExcelApplication.Workbooks.Open(Path.GetFullPath(filename), ReadOnly:true);
            if (WorkBook.Worksheets.Count == 0)
            {
                throw new Exception(String.Format("Excel sheet {0} has no visible worksheets", filename));
            }
            WorkSheet = WorkBook.ActiveSheet;
            TotalRows = WorkSheet.UsedRange.Rows.Count;
            var lastUsedColumn = WorkSheet.Cells.Find("*", System.Reflection.Missing.Value,
                               System.Reflection.Missing.Value, System.Reflection.Missing.Value,
                               Excel.XlSearchOrder.xlByColumns, Excel.XlSearchDirection.xlPrevious,
                               false, System.Reflection.Missing.Value, System.Reflection.Missing.Value).Column;
            TotalColumns = lastUsedColumn + 1;
        }
        ~MicrosoftExcelAdapter()  
        {
            GC.Collect();
            GC.WaitForPendingFinalizers();

            if (WorkSheet != null)
            {
                Marshal.ReleaseComObject(WorkSheet);
            }
            if (WorkBook != null)
            {
                WorkBook.Close();
                Marshal.ReleaseComObject(WorkBook);
            }
            if (ExcelApplication != null)
            {
                ExcelApplication.Quit();
                Marshal.FinalReleaseComObject(ExcelApplication);
            }
        }


        public override Cell GetCell(int row, int column)
        {
            Excel.Range cell = WorkSheet.Cells[row + 1, column + 1];
            return new MSExcelCell(cell, WorkSheet.Columns[column + 1].ColumnWidth);
        }

        public override int GetRowsCount()
        {
            if (MaxRowsToProcess != -1)
            {
                return Math.Min(MaxRowsToProcess, TotalRows);
            }

            return TotalRows;
        }

        public override int GetColsCount()
        {
            return TotalColumns;
        }

        public override string GetTitleOutsideTheTable()
        {
            return "";
        }

        public override List<Cell> GetCells(int rowIndex, int maxColEnd = -1)
        {
            List<Cell> result = new List<Cell>();
            for (int i = 1; i < TotalColumns; i++)
            {
                int width = WorkSheet.Columns.ColumnWidth[i];
                Cell cell = new MSExcelCell( WorkSheet.Cells.Cells[rowIndex + 1, i], width);
                result.Add(cell);
                if (cell.IsMerged && cell.MergedColsCount > 1)
                {
                    i += cell.MergedColsCount - 1;
                }

                //result.Add(new MSExcelCell(c));
            }
            if (result.Count == 0)
            {
                return null;
            }
            return result;
        }
    }
}
#endif