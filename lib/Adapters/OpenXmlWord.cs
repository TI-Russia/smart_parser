using System;
using System.Net;
using System.IO;
using System.Threading;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Xml;
using System.Text;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;

using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Parser.Lib;
using System.Security.Cryptography;

namespace Smart.Parser.Adapters
{
    class TableWidthInfo
    {
        public int TableWidthInPixels;
        public int TableIndentionInPixels = 0;
        public List<int> ColumnWidths;
        public static int DxaToPixels(int dxa)
        {
            double points = dxa / 20.0;
            return (int)(((double)points) * 96.0 / 72.0);
        }
        public static int TryReadWidth(string val, TableWidthUnitValues widthType, int parentWidthInPixels)
        {
            try
            {
                if (widthType == TableWidthUnitValues.Pct)
                {
                    double pct = Int32.Parse(val);
                    double ratio = pct / 5000.0;
                    double pxels = parentWidthInPixels * ratio;
                    return (int)pxels;
                }
                if (widthType != TableWidthUnitValues.Dxa && widthType != TableWidthUnitValues.Auto)
                {
                    Console.WriteLine("unknown TableWidthUnitValues");
                    return 0;
                }
                return DxaToPixels((int)Int32.Parse(val));
            }
            catch (Exception)
            {
                return 0;
            }
        }

    }
    class OpenXmlWordCell : Cell
    {
        public bool IsVerticallyMerged;

        public OpenXmlWordCell(TableWidthInfo tableWidth, TableCell inputCell, int row, int column)
        {
            var cellContents = GetCellText(inputCell);
            var vmerge = inputCell.TableCellProperties.GetFirstChild<VerticalMerge>();
            if (vmerge == null)
            {
                IsVerticallyMerged = false;
            }
            else
            {
                if (vmerge == null || vmerge.Val == null || vmerge.Val == MergedCellValues.Continue)
                {
                    IsVerticallyMerged = true;
                }
                else
                {
                    //vmerge.Val == MergedCellValues.Restart
                    IsVerticallyMerged = false;
                }
            }
            var gridSpan = inputCell.TableCellProperties.GetFirstChild<GridSpan>();
            IsMerged = gridSpan != null && gridSpan.Val > 1;
            FirstMergedRow = -1; // init afterwards
            MergedRowsCount = -1; // init afterwards

            MergedColsCount = (gridSpan == null) ? 1 : (int)gridSpan.Val;
            IsEmpty = cellContents.IsNullOrWhiteSpace();
            Text = cellContents;
            Row = row;
            Col = column;
            if (inputCell.TableCellProperties != null
                && inputCell.TableCellProperties.TableCellWidth != null
                && inputCell.TableCellProperties.TableCellWidth.Type != null
                && inputCell.TableCellProperties.TableCellWidth.Type != TableWidthUnitValues.Auto
                )
            {
                CellWidth = TableWidthInfo.TryReadWidth(
                    inputCell.TableCellProperties.TableCellWidth.Width,
                    inputCell.TableCellProperties.TableCellWidth.Type,
                    tableWidth.TableWidthInPixels);
            }
            else
            {
                if (Col < tableWidth.ColumnWidths.Count)
                {
                    CellWidth = tableWidth.ColumnWidths[Col];
                }
            }
            AdditTableIndention = tableWidth.TableIndentionInPixels;
        }
        public OpenXmlWordCell(IAdapter.TJsonCell cell)
        {
            Text = cell.t;
            MergedColsCount = cell.mc;
            MergedRowsCount = cell.mr;
            IsVerticallyMerged = MergedRowsCount > 1;
            IsEmpty = Text.IsNullOrWhiteSpace();
            Row = cell.r;
            Col = cell.c;
        }

        public static string GetCellText(OpenXmlElement inputCell)
        {
            string s = "";
            foreach (var p in inputCell.Elements<Paragraph>())
            {
                foreach (var textOrBreak in p.Descendants())
                {
                    if (textOrBreak.LocalName == "t")
                    {
                        s += textOrBreak.InnerText;
                    }
                    else if (textOrBreak.LocalName == "cr")
                    {
                        s += "\n";
                    }
                    else if (textOrBreak.LocalName == "br")
                    /* do  not use lastRenderedPageBreak, see MinRes2011 for wrong lastRenderedPageBreak in Семенов 
                    ||
                          (textOrBreak.Name == w + "lastRenderedPageBreak") */
                    {
                        s += "\n";
                    }
                }
                s += "\n";
            }
            return s;

        }
    }

    public class OpenXmlWordAdapter : IAdapter
    {
        private List<List<OpenXmlWordCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private static readonly string WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
        private static Dictionary<string, double> Bigrams = ReadBigrams();
        XmlNamespaceManager NamespaceManager;
        private int TablesCount;
        private int DocumentPageSizeInPixels;
        private int DocumentPageLeftMaginInPixels = 0;
        private static string ToHex(byte[] bytes)
        {
            StringBuilder result = new StringBuilder(bytes.Length * 2);

            for (int i = 0; i < bytes.Length; i++)
                result.Append(bytes[i].ToString("x2"));

            return result.ToString();
        }

        string DowloadFromConvertedStorage(string filename)
        {
            using (SHA256 mySHA256 = SHA256.Create())
            {
                string hashValue;
                using (FileStream fileStream = File.Open(filename, FileMode.Open))
                {
                    hashValue = ToHex(mySHA256.ComputeHash(fileStream));
                }
                using (var client = new WebClient())
                {
                    string url = ConvertedFileStorageUrl + "?sha256=" + hashValue;
                    string docXPath = Path.GetTempFileName();
                    Logger.Debug(String.Format("try to download docx from {0} to {1}", url, docXPath));
                    client.DownloadFile(url, docXPath);

                    return docXPath;
                }

            }
        }



        string ConvertFile2TempDocX(string filename)
        {
            if (ConvertedFileStorageUrl != "" && filename.EndsWith("pdf"))
            {
                try
                {
                    return DowloadFromConvertedStorage(filename);
                }
                catch (Exception ) {
                    // a new file try to load it into Microsoft Word
                }
            }
            Aspose.Words.Document doc = new Aspose.Words.Document(filename);
            doc.RemoveMacros();
            // use libre office when aspose is not accessible
            // "soffice --headless --convert-to docx docum.doc"
            // string docXPath = Path.GetTempFileName();
            string docXPath = filename + ".converted.docx";
            doc.Save(docXPath, Aspose.Words.SaveFormat.Docx);
            return docXPath;
        }

        static Dictionary<string, double> ReadBigrams()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            var result = new Dictionary<string, double>();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.bigrams.txt"))
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

        public OpenXmlWordAdapter(string fileName, int maxRowsToProcess)
        {
            NamespaceManager = new XmlNamespaceManager(new NameTable());
            NamespaceManager.AddNamespace("w", WordXNamespace);

            TableRows = new List<List<OpenXmlWordCell>>();

            if (fileName.EndsWith(".toloka_json"))
            {
                InitFromJson(fileName);
                InitUnmergedColumnsCount();
                return;
            }
            DocumentFile = fileName;
            string extension = Path.GetExtension(fileName).ToLower();
            bool removeTempFile = false;
            if (    extension == ".html"
                ||  extension == ".htm"
                || extension == ".xhtml"
                || extension == ".pdf"
                || extension == ".doc"
                || extension == ".rtf"
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


            using (var doc = WordprocessingDocument.Open(fileName,  false))
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
            return new OpenXmlWordAdapter(fileName, maxRowsToProcess);
        }

        private void FindTitleAboveTheTable(WordprocessingDocument wordDocument)
        {
            Title = "";
            var body = wordDocument.MainDocumentPart.Document.Body;
            foreach (var p in wordDocument.MainDocumentPart.Document.Descendants<Paragraph>())
            {
                if (p.Parent != body)
                {
                    break;
                }
                Title += p.InnerText + "\n";
            }
        }

        void CopyPortion(List<List<TJsonCell>> portion, bool ignoreMergedRows)
        {
            for (int i = 0;  i < portion.Count; i++)
            {
                var r = portion[i];
                List<OpenXmlWordCell> newRow = new List<OpenXmlWordCell>();

                foreach (var c in r)
                {
                    var cell = new OpenXmlWordCell(c);
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

        static bool CheckMergeRow(List<OpenXmlWordCell> row1, List<OpenXmlWordCell> row2)
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
                        Logger.Debug(string.Format(
                            "Join rows using mutual information on cells \"{0}\" and \"{1}\"", 
                            row1[i].Text.ReplaceEolnWithSpace(), 
                            row2[i].Text.ReplaceEolnWithSpace()));
                        return true;
                    }
                }
            }
            return false;
        }
        static void MergeRow(List<OpenXmlWordCell> row1, List<OpenXmlWordCell> row2)
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

        int GetRowGridBefore(TableRow row)
        {
            if (row.TableRowProperties != null)
                foreach (var c in row.TableRowProperties.Descendants<GridBefore>())
                {
                    return c.Val;
                }
            return 0;
        }

        TableWidthInfo InitializeTableWidthInfo(Table table)
        {
            TableWidthInfo widthInfo = new TableWidthInfo();
            TableProperties tProp = table.GetFirstChild<TableProperties>();
            if (tProp != null) {
                if (tProp.TableWidth != null)
                {
                    widthInfo.TableWidthInPixels = TableWidthInfo.TryReadWidth(
                        tProp.TableWidth.Width,
                        tProp.TableWidth.Type,
                        DocumentPageSizeInPixels);
                }

                if (tProp.TableIndentation != null)
                {
                    widthInfo.TableIndentionInPixels = TableWidthInfo.TryReadWidth(
                        tProp.TableIndentation.Width,
                        tProp.TableIndentation.Type,
                        DocumentPageSizeInPixels);
                }
                widthInfo.TableIndentionInPixels += DocumentPageLeftMaginInPixels;
            }
            else
            {
                widthInfo.TableWidthInPixels  =  this.DocumentPageSizeInPixels;
            }
            TableGrid tGrid = table.GetFirstChild<TableGrid>();
            if (tGrid != null)
            {
                widthInfo.ColumnWidths = new List<int>();
                foreach (var col in tGrid.Elements<GridColumn>())
                {
                    widthInfo.ColumnWidths.Add(
                        TableWidthInfo.TryReadWidth(
                            col.Width, 
                            TableWidthUnitValues.Dxa,
                            widthInfo.TableWidthInPixels));

                }
            }
            return widthInfo;
        }
        void ProcessWordTable(Table table, int maxRowsToProcess)
        {
            var rows = table.Descendants<TableRow>().ToList();
            TableWidthInfo widthInfo = InitializeTableWidthInfo(table);
            int saveRowsCount = TableRows.Count;
            int maxCellsCount = 0;
            for (int r = 0; r < rows.Count(); ++r)
            {
                List<OpenXmlWordCell> newRow = new List<OpenXmlWordCell>();
                int sumspan = 0;
                var row = rows[r];
                int rowGridBefore = GetRowGridBefore(row);
                bool isEmpty = true;
                foreach (var rowCell in row.Elements<TableCell>() )
                {
                    var c = new OpenXmlWordCell(widthInfo, rowCell, TableRows.Count, sumspan);
                    if (newRow.Count == 0)
                        c.MergedColsCount += rowGridBefore;
                    newRow.Add(c);
                    sumspan += c.MergedColsCount;
                    isEmpty = isEmpty && c.IsEmpty;
                }
                if (isEmpty)
                {
                    continue;
                }
                maxCellsCount = Math.Max(newRow.Count, maxCellsCount);
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
            if (maxCellsCount <= 4)
            {
                //remove this suspicious table 
                TableRows.RemoveRange(saveRowsCount, TableRows.Count - saveRowsCount);
            }
        }
        
        void InitPageSize(WordprocessingDocument wordDocument)
        {
            var docPart = wordDocument.MainDocumentPart;
            var pageSize = docPart.Document.Descendants<PageSize>().FirstOrDefault();
            int pageDxa = 11906; // letter size is ISO 216 A4 (210x297mm
            if (pageSize != null)
            {
                pageDxa = (int)(uint)pageSize.Width;
            }
            DocumentPageSizeInPixels = TableWidthInfo.DxaToPixels(pageDxa);

            var pageMargin = docPart.Document.Descendants<PageMargin>().FirstOrDefault();
            int pageMarginDxa = 0; // letter size is ISO 216 A4 (210x297mm
            if (pageMargin != null && pageMargin.Left != null)
            {
                pageMarginDxa = (int)(uint)pageMargin.Left;
            }
            DocumentPageLeftMaginInPixels = TableWidthInfo.DxaToPixels(pageMarginDxa);
        }

        void ProcessWordTableAndUpdateTitle(Table table, int maxRowsToProcess, int tableIndex)
        {
            int debugSaveRowCount = TableRows.Count;
            if (table.Descendants<Table>().ToList().Count > 0)
            {
                Logger.Debug(String.Format("ignore table {0} with subtables", tableIndex));
            }
            else
            {
                ProcessWordTable(table, maxRowsToProcess);
            }
            if (table.InnerText.Length > 30 && TableRows.Count > debugSaveRowCount)
            {
                Logger.Debug(String.Format("add {0} rows from table {1} Table.innertText[0:30]='{2}...'",
                    TableRows.Count - debugSaveRowCount,
                    tableIndex,
                    table.InnerText.Substring(0, 30)));
            }
            if (Title.Length == 0 && table.InnerText.Length > 30 && table.InnerText.ToLower().IndexOf("декабря") != -1)
            {
                var rows = new List<String>();
                foreach (var r in table.Descendants<TableRow>())
                {
                    rows.Add(r.InnerText);
                }
                Title = String.Join("\n", rows);
            }
        }

        void CollectRows(WordprocessingDocument wordDocument, int maxRowsToProcess)
        {
            var docPart = wordDocument.MainDocumentPart;
            InitPageSize(wordDocument);
            var tables = docPart.Document.Descendants<Table>();
            TablesCount = tables.Count();
            int tableIndex = 0;
            foreach (OpenXmlPart h in docPart.HeaderParts)
            {
                foreach (var t in h.RootElement.Descendants<Table>()) {
                    ProcessWordTableAndUpdateTitle(t, maxRowsToProcess, tableIndex);
                    tableIndex++;
                }

            }

            foreach (var t in tables)
            {
                ProcessWordTableAndUpdateTitle(t, maxRowsToProcess, tableIndex);
                tableIndex++;
            }
        }


        public override List<Cell> GetCells(int row, int maxColEnd = IAdapter.MaxColumnsCount)
        {
            var result = new List<Cell>();
            foreach (var r in TableRows[row])
            {
                //if (r.Col >= maxColEnd)
                //{
                //    break;
                //}
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


