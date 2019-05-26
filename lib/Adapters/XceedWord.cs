using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.Linq;
using System.Xml.Linq;
using System.Text;
using TI.Declarator.ParserCommon;

using Microsoft.Office.Interop.Word;
using Xceed.Words.NET;

namespace Smart.Parser.Adapters
{
    class XceedWordCell : Cell
    {
        public bool HasTopBorder;

        public XceedWordCell(Xceed.Words.NET.Cell inputCell, int row, int column)
        {   
            var cellContents = GetXceedText(inputCell);
            var vmerge = inputCell.Xml.Descendants().FirstOrDefault(d => d.Name.LocalName.ToLower() == "vmerge");
            if (vmerge != null)
            {
                HasTopBorder = (vmerge?.Attributes().FirstOrDefault(a => a.Name.LocalName == "val")?.Value ?? string.Empty) == "restart"; ; 
            }
            else
            {
                HasTopBorder = true;
            }

            IsMerged = inputCell.GridSpan > 1;
            FirstMergedRow = -1; // init afterwards
            MergedRowsCount = -1; // init afterwards

            MergedColsCount = inputCell.GridSpan;
            IsHeader = false;
            IsEmpty = cellContents.IsNullOrWhiteSpace();
            BackgroundColor = null;
            ForegroundColor = null;
            Text = cellContents;
            Row = row;
            Col = column;
        }

        static string GetXceedText(Xceed.Words.NET.Cell inputCell)
        {
            string s = "";
            foreach (var p in inputCell.Paragraphs)
            {
                s += p.Text + "\n";
            }
            return s;
        }
    }

    public class XceedWordAdapter : IAdapter
    {
        private List<List<XceedWordCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private static readonly XNamespace WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

        string ConvertFile2TempDocX(string filename)
        {
            Application word = new Application();
            var doc = word.Documents.Open(Path.GetFullPath(filename));
            string docXPath = Path.GetTempFileName();
            doc.SaveAs2(docXPath, WdSaveFormat.wdFormatXMLDocument, CompatibilityMode: WdCompatibilityMode.wdWord2013);
            word.ActiveDocument.Close();
            word.Quit();
            return docXPath;
        }

        public XceedWordAdapter(string fileName, int maxRowsToProcess)
        {
            string extension = Path.GetExtension(fileName);
            bool removeTempFile = false;
            if (    extension == ".html"
                ||  extension == ".pdf"
                || extension == ".doc"
                )
            {
                fileName = ConvertFile2TempDocX(fileName);
                removeTempFile = true;
            }

            using (DocX doc = DocX.Load(fileName))
            {
                FindTitle(doc);
                CollectRows(doc, maxRowsToProcess);
            };
            if (removeTempFile)
            {
                File.Delete(fileName);
            }
        }
        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess)
        {
            return new XceedWordAdapter(fileName, maxRowsToProcess);
        }

        private void FindTitle(DocX wordDocument)
        {
            Title = "";
            foreach (var p in wordDocument.Paragraphs)
            {
                if (p.ParentContainer != Xceed.Words.NET.ContainerType.Body)
                {
                    break;
                }
                Title += p.Text + "\n";
            }
        }


        public override string GetTitle()
        {
            return Title;
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

        int FindFirstBorderGoingUp(int startRow, int column)
        {
            for (int i = startRow; i > 0; --i)
            {
                int cellNo = FindMergedCellByColumnNo(i, column);
                if (TableRows[i][cellNo].HasTopBorder)
                {
                    return i;
                }
                if (i == 0)
                {
                    return i;
                }
            }
            return 0;
        }

        int FindFirstBorderGoingDown(int startRow, int column)
        {
            for (int i = startRow; i < TableRows.Count; ++i)
            {
                int cellNo = FindMergedCellByColumnNo(i, column);
                if (i > startRow && TableRows[i][cellNo].HasTopBorder)
                {
                    return i - 1;
                }
                if (i+1 == TableRows.Count)
                {
                    return i;
                }
            }
            return TableRows.Count - 1;
        }


        void CollectRows(DocX wordDocument, int maxRowsToProcess)
        {
            TableRows = new List<List<XceedWordCell>>();
            UnmergedColumnsCount = -1;
            foreach (var table in wordDocument.Tables)
            {
                foreach (var row in table.Rows)
                {
                    List<XceedWordCell> newRow = new List<XceedWordCell>();
                    int sumspan = 0;
                    foreach (var rowCell in row.Cells)
                    {
                        var c = new XceedWordCell(rowCell, TableRows.Count, sumspan);
                        newRow.Add(c);
                        sumspan += c.GridSpan == 0 ? 1 : c.GridSpan;
                    }
                    TableRows.Add(newRow);
                    if (UnmergedColumnsCount == -1)
                    {
                        UnmergedColumnsCount = sumspan;
                    }
                    if ((maxRowsToProcess != -1) && (TableRows.Count >= maxRowsToProcess)) {
                        break;
                    }
                }
            }
            foreach (var r in TableRows)
            {
                foreach (var c in r) {
                    c.FirstMergedRow = FindFirstBorderGoingUp(c.Row, c.Col);
                    c.MergedRowsCount = FindFirstBorderGoingDown(c.Row, c.Col) - c.Row + 1; 
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

        public override Cell GetCell(int row, int column)
        {
            int cellNo = FindMergedCellByColumnNo(row, column);
            if (cellNo == -1) return null;
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


