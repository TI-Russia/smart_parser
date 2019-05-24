using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using System.Xml.Linq;
using System.Text;

using TI.Declarator.ParserCommon;

using Xceed.Words.NET;
using Microsoft.Office.Interop.Word;


namespace Smart.Parser.Adapters
{
    class XCeedWordCell : Cell
    {
        public bool HasTopBorder;
        public bool HasBottomBorder;
        private bool HasBorder(Xceed.Words.NET.Cell xceedCell, TableCellBorderType border)
        {
            try
            {
                var dummy = xceedCell.GetBorder(border);
                return true;
            }
            catch (Exception e)
            {
                return false;
            }
        }

        public XCeedWordCell(Xceed.Words.NET.Cell xceedCell, int row, int column)
        {
            var cellContents = GetXceedText(xceedCell);
            //var dummy = xceedCell.Xml.ToString();
            HasTopBorder = HasBorder(xceedCell, TableCellBorderType.Top);
            HasBottomBorder = HasBorder(xceedCell, TableCellBorderType.Bottom);

            IsMerged = xceedCell.GridSpan > 0;
            FirstMergedRow = -1; // init afterwards
            MergedRowsCount = -1; // init afterwards

            MergedColsCount = xceedCell.GridSpan == 0 ? 1 : xceedCell.GridSpan;
            IsHeader = false;
            IsEmpty = cellContents.IsNullOrWhiteSpace();
            BackgroundColor = null;
            ForegroundColor = null;
            Text = cellContents;
            Row = row;
            Col = column;
        }

        static string GetXceedText(Xceed.Words.NET.Cell xceedCell)
        {
            var res = new StringBuilder();
            foreach (var p in xceedCell.Paragraphs)
            {
                res.Append(p.Text);
                res.Append("\n");
            }
            return res.ToString();
        }
    }

    public class XceedWordAdapter : IAdapter
    {
        private List<List<XCeedWordCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private static readonly XNamespace WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
        public XceedWordAdapter(string filename, int maxRowsToProcess)
        {
            DocX doc = DocX.Load(filename);
            Title =  FindTitle(doc);
            CollectRows(doc, maxRowsToProcess);
        }

        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess)
        {
            return new XceedWordAdapter(fileName, maxRowsToProcess);
        }

        private string FindTitle(DocX doc)
        {
            var docBody = doc.Xml.Elements(WordXNamespace + "body");
            var titleParagraphs = doc.Xml.Elements().TakeWhile(el => el.Name.ToString() != $"{{{WordXNamespace}}}tbl");

            return titleParagraphs.Select(p => p.Value)
                                  .Aggregate("", (str1, str2) => str1 + '\n' + str2);
        }


        int FindMergedCellByColumnNo(int row, int column)
        {
            var r = TableRows[row];
            int sumspan = 0;
            for (var i = 0; i < r.Count; ++i)
            {
                int span = r[i].GridSpan == 0 ? 1 : r[i].GridSpan;
                if ((column >= sumspan) && (column < sumspan + span))
                    return i;
                sumspan += span;
            }
            return -1;
        }

        int FindFirstCellWithTopBorder(int row, int column)
        {
            for (int i = row; i > 0; --i)
            {
                int cellNo = FindMergedCellByColumnNo(row, column);
                if (TableRows[row][cellNo].HasTopBorder)
                {
                    return row;
                }
            }
            return 0;
        }


        void CollectRows(DocX doc, int maxRowsToProcess)
        {
            TableRows = new List<List<XCeedWordCell>>();
            UnmergedColumnsCount = -1; 
            foreach (var table in doc.Tables)
            {
                foreach (var r in table.Rows)
                {
                    if (UnmergedColumnsCount == -1)
                    {
                        UnmergedColumnsCount = r.ColumnCount;
                    }
                    List<XCeedWordCell> newRow = new List<XCeedWordCell>();
                    int sumspan = 0;
                    foreach (var c in r.Cells)
                    {
                        newRow.Add(new XCeedWordCell(c, TableRows.Count, sumspan));
                        sumspan += c.GridSpan == 0 ? 1 : c.GridSpan;
                    }
                    TableRows.Add(newRow);
                    if ((maxRowsToProcess !=- -1) && (TableRows.Count >= maxRowsToProcess)) {
                        break;
                    }
                }
            }
            foreach (var r in TableRows)
            {
                foreach (var c in r) {
                    c.FirstMergedRow = FindFirstCellWithTopBorder(c.Row, c.Col);
                    c.MergedRowsCount = FindFirstCellWithBottomBorder(c.Row, c.Col) - c.FirstMergedRow + 1; 
                }
            }
        }


        public override List<Cell> GetCells(int row)
        {
            var result = new List<Cell>();
            foreach (var r in TableRows[row])
            {
                result.Add(r);
            }
            return result;
        }

        int FindFirstCellWithBottomBorder(int row, int column)
        {
            for (int i = row; i < TableRows.Count; ++i)
            {
                int cellNo = FindMergedCellByColumnNo(row, column);
                if (TableRows[row][cellNo].HasBottomBorder)
                {
                    return row;
                }
            }
            return 0;
        }

        public override Cell GetCell(int row, int column)
        {
            int cellNo = FindMergedCellByColumnNo(row, column);

            return  TableRows[row][cellNo];
        }


        public override int GetRowsCount()
        {
            return TableRows.Count;
        }

        public override int GetColsCount()
        {
            return UnmergedColumnsCount;
        }

        public override int GetColsCount(int row)
        {
            return GetCells(row).Count;
        }
    }
}
