using System;
using System.IO;
using System.Threading;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Xml.Linq;
using System.Xml.XPath;
using System.Xml;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;

using Microsoft.Office.Interop.Word;
using Xceed.Words.NET;
using Parser.Lib;


namespace Smart.Parser.Adapters
{
    class XceedWordCell : Cell
    {
        public bool IsVerticallyMerged;
        
        public XceedWordCell(Xceed.Words.NET.Cell inputCell, int row, int column)
        {   
            var cellContents = GetXceedText(inputCell);
            var vmerge = inputCell.Xml.Descendants().FirstOrDefault(d => d.Name.LocalName.ToLower() == "vmerge");
            if (vmerge != null)
            {
                IsVerticallyMerged = (vmerge?.Attributes().FirstOrDefault(a => a.Name.LocalName == "val")?.Value ?? string.Empty) != "restart";
            }
            else
            {
                IsVerticallyMerged = false;
            }

            IsMerged = inputCell.GridSpan > 1;
            FirstMergedRow = -1; // init afterwards
            MergedRowsCount = -1; // init afterwards

            MergedColsCount = inputCell.GridSpan == 0 ? 1 : inputCell.GridSpan;
            IsEmpty = cellContents.IsNullOrWhiteSpace();
            Text = cellContents;
            Row = row;
            Col = column;
            CellWidth = (int)inputCell.Width;
        }
        public XceedWordCell(IAdapter.TJsonCell cell)
        {
            Text = cell.t;
            MergedColsCount = cell.mc;
            MergedRowsCount = cell.mr;
            IsVerticallyMerged = MergedRowsCount > 1;
            IsEmpty = Text.IsNullOrWhiteSpace();
            Row = cell.r;
            Col = cell.c;
        }

        public static string GetXceedText(Xceed.Words.NET.Cell inputCell)
        {
            string s = "";
            foreach (var p in inputCell.Paragraphs)
            {
                XElement e = p.Xml;
                XNamespace w = e.Name.Namespace;
                foreach (var textOrBreak in e.Descendants())
                {
                    if (textOrBreak.Name == w + "t")
                    {
                        s += textOrBreak.Value;
                    }
                    else if (   (textOrBreak.Name == w + "br")
                                            /* do  not use lastRenderedPageBreak, see MinRes2011 for wrong lastRenderedPageBreak in Семенов 
                                            ||
                                                  (textOrBreak.Name == w + "lastRenderedPageBreak") */)
                    {
                        s += "\n";
                    }
                }
                s += "\n";
            }
            return s;
        }
        
    }


    public class XceedWordAdapter : IAdapter
    {
        private List<List<XceedWordCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private static readonly string WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
        private static Dictionary<string, double> Bigrams = ReadBigrams();
        XmlNamespaceManager NamespaceManager;
        private int TablesCount;

        string ConvertFile2TempDocX(string filename)
        {
            Application word = new Application();
            var doc = word.Documents.OpenNoRepairDialog(Path.GetFullPath(filename),ReadOnly:true, ConfirmConversions:false);
            string docXPath;
            if (ConvertedFileDir != null)
            {
                docXPath = Path.Combine(ConvertedFileDir, Path.GetFileNameWithoutExtension(filename) + ".docx");
            }
            else
            {
                docXPath = Path.GetTempFileName();
            }


            doc.SaveAs2(docXPath, WdSaveFormat.wdFormatXMLDocument, CompatibilityMode: WdCompatibilityMode.wdWord2013);
            word.ActiveDocument.Close();
            word.Quit();
            return docXPath;
        }
        static Dictionary<string, double> ReadBigrams()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            var result = new Dictionary<string, double>();
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.bigrams.txt"))
            {
                using (var reader = new StreamReader(stream))
                {
                    while (reader.Peek() >= 0)
                    {
                        var line = reader.ReadLine();
                        var parts = line.Split('\t');
                        double mutual_information = Convert.ToDouble(parts[1]);
                        if (mutual_information > 0)
                        {
                            result[parts[0]] = mutual_information;
                        }
                    }
                }
            }
            return result;
        }

        public XceedWordAdapter(string fileName, int maxRowsToProcess)
        {
            NamespaceManager = new XmlNamespaceManager(new NameTable());
            NamespaceManager.AddNamespace("w", WordXNamespace);

            TableRows = new List<List<XceedWordCell>>();

            if (fileName.EndsWith(".toloka_json"))
            {
                InitFromJson(fileName);
                InitUnmergedColumnsCount();
                return;
            }
            DocumentFile = fileName;
            string extension = Path.GetExtension(fileName);
            bool removeTempFile = false;
            if (    extension == ".html"
                ||  extension == ".pdf"
                || extension == ".doc"
                )
            {
                try
                {
                    fileName = ConvertFile2TempDocX(fileName);
                }catch (Exception) {
                    Thread.Sleep(10000); //10 seconds
                    fileName = ConvertFile2TempDocX(fileName);
                }
                removeTempFile = false;
            }


            using (DocX doc = DocX.Load(fileName))
            {
                FindTitleAboveTheTable(doc);
                CollectRows(doc, maxRowsToProcess);
                InitUnmergedColumnsCount();
                InitializeVerticallyMerge();
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

        private void FindTitleAboveTheTable(DocX wordDocument)
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

        void CopyPortion(List<List<TJsonCell>> portion, bool ignoreMergedRows)
        {
            for (int i = 0;  i < portion.Count; i++)
            {
                var r = portion[i];
                List<XceedWordCell> newRow = new List<XceedWordCell>();

                foreach (var c in r)
                {
                    var cell = new XceedWordCell(c);
                    cell.Row = TableRows.Count;
                    if (ignoreMergedRows)
                    {
                        cell.MergedRowsCount = 1;
                    }
                    cell.CellWidth = 10; //  no cell width serialized in html
                    newRow.Add(cell);
                }
                TableRows.Add(newRow);
            }

        }
        private void InitFromJson(string fileName)
        {
            string jsonStr;
            using (StreamReader r = new StreamReader(fileName))
            {
                jsonStr = r.ReadToEnd();
            }
            TJsonTablePortion portion = JsonConvert.DeserializeObject<TJsonTablePortion>(jsonStr);
            Title = portion.Title;
            DocumentFile = portion.InputFileName;
            CopyPortion(portion.Header, false);
            CopyPortion(portion.Section, true);
            CopyPortion(portion.Data, true);
        }

        public override string GetTitleOutsideTheTable()
        {
            return Title;
        }

        int FindMergedCellByColumnNo(int row, int column)
        {
            var r = TableRows[row];
            int sumspan = 0;
            for (var i = 0; i < r.Count; ++i)
            {
                int span = r[i].MergedColsCount;
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
                if (cellNo == -1)
                {
                    return i + 1;
                }
                if (!TableRows[i][cellNo].IsVerticallyMerged)
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
                if (cellNo == -1)
                {
                    return i - 1;
                }
                if (i > startRow && !TableRows[i][cellNo].IsVerticallyMerged)
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

        void InitializeVerticallyMerge()
        {
            foreach (var r in TableRows)
            {
                foreach (var c in r)
                {
                    try
                    {
                        c.FirstMergedRow = FindFirstBorderGoingUp(c.Row, c.Col);
                        c.MergedRowsCount = FindFirstBorderGoingDown(c.Row, c.Col) - c.Row + 1;
                    }
                    catch (Exception e)
                    {
                        Console.WriteLine(string.Format("Parsing Exception row{0} col={1}: {2}", c.Row, c.Col, e.ToString()));
                        throw;
                    }

                }
            }
        }

        static List<string> TokenizeCellText(string text)
        {
            List<string> result = new List<string>();
            foreach (var token in text.Split())
            {
                token.Trim(
                    '﻿', ' ', // two different spaces
                    '\n', '\r', 
                    ',', '!', '.', '{', '}',
                    '[', ']', '(', ')',
                    '"', '«', '»', '\'');
                if (token.Count() > 0) result.Add(token);
            }
            return result;
        }

        static bool CheckMergeRow(List<XceedWordCell> row1, List<XceedWordCell> row2)
        {
            if (row1.Count != row2.Count)
            {
                return false;
            }
            for (int i = 0; i < row1.Count; ++i)
            {
                var tokens1 = TokenizeCellText(row1[i].Text);
                var tokens2 = TokenizeCellText(row2[i].Text);
                if (tokens1.Count > 0 && tokens2.Count > 0)
                {
                    string key = tokens1.Last() + " " + tokens2.First();
                    if (Bigrams.ContainsKey(key))
                    {
                        Logger.Debug(string.Format("Join rows using mutual information on cells \"{0}\" and \"{1}\"", row1[i].GetTextOneLine(), row2[i].GetTextOneLine()));
                        return true;
                    }
                }
            }
            return false;
        }
        static void MergeRow(List<XceedWordCell> row1, List<XceedWordCell> row2)
        {
            for (int i = 0; i < row1.Count; ++i)
            {
                row1[i].Text += "\n" + row2[i].Text;
            }
        }

        void InitUnmergedColumnsCount()
        {
            UnmergedColumnsCount = -1;
            if (TableRows.Count > 0)
            {
                UnmergedColumnsCount = 0;
                foreach (var c in TableRows[0]) {
                    UnmergedColumnsCount += c.MergedColsCount;
                }
            }
        }

        int GetRowGridBefore(Xceed.Words.NET.Row row)
        {
            try
            {
                var el = ((IEnumerable<object>)row.Xml.XPathEvaluate("./w:trPr/w:gridBefore/@w:val", NamespaceManager))
                                    .OfType<XAttribute>()
                                    .Single()
                                    .Value; ;
               return Int32.Parse(el);
            }
            catch (Exception)
            {
            }
            return 0;
        }
        
        void ProcessWordTable(Xceed.Words.NET.Table table, int maxRowsToProcess)
        {
            for (int r = 0; r < table.Rows.Count; ++r)
            {
                List<XceedWordCell> newRow = new List<XceedWordCell>();
                int sumspan = 0;
                var row = table.Rows[r];
                int rowGridBefore = GetRowGridBefore(row);
                var cells = row.Cells;

                foreach (var rowCell in cells)
                {
                    var c = new XceedWordCell(rowCell, TableRows.Count, sumspan);
                    if (newRow.Count == 0)
                        c.MergedColsCount += rowGridBefore;
                    newRow.Add(c);
                    sumspan += c.MergedColsCount;
                }
                if (r == 0 && TableRows.Count > 0 && CheckMergeRow(TableRows.Last(), newRow))
                {
                    MergeRow(TableRows.Last(), newRow);
                }
                else
                {
                    TableRows.Add(newRow);
                }

                if ((maxRowsToProcess != -1) && (TableRows.Count >= maxRowsToProcess))
                {
                    break;
                }
            }
        }
        
        void CollectRows(DocX wordDocument, int maxRowsToProcess)
        {
            TablesCount = wordDocument.Tables.Count;
            Header first = wordDocument.Headers.First;
            if (first != null)
            {
                foreach (var t in first.Tables)
                {
                    ProcessWordTable(t, maxRowsToProcess);
                }
            }

            foreach (var t in wordDocument.Tables)
            {
                ProcessWordTable(t, maxRowsToProcess);
            }
        }


        public override List<Cell> GetCells(int row, int maxColEnd = IAdapter.MaxColumnsCount)
        {
            var result = new List<Cell>();
            foreach (var r in TableRows[row])
            {
                if (r.Col >= maxColEnd)
                {
                    break;
                }
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

        public override int GetTablesCount()
        {
            return TablesCount;
        }

    }
}


