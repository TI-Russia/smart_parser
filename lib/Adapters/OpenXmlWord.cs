using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Newtonsoft.Json;
using Smart.Parser.Lib;
using Smart.Parser.Lib.Adapters.AdapterSchemes;
using Smart.Parser.Lib.Adapters.DocxSchemes;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Xml;
using System.Xml.Linq;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{
    public class TableWidthInfo
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

    public class BadCellAddress : System.Exception 
    {
        public int Row = -1;
        public BadCellAddress(int row, int col) 
                : base(String.Format("Cannot get cell row={0}, col={1} ", row, col)) 
        {
            Row = row;
        }
    }

    public class WordDocHolder : IDisposable
    {
        public WordprocessingDocument WordDocument;
        public int DocumentPageSizeInPixels;
        public int DocumentPageLeftMaginInPixels = 0;
        public int DefaultFontSize = 10;
        public string DefaultFontName = "Times New Roman";
        bool disposed = false;
        public WordDocHolder(WordprocessingDocument wordDocument)
        {
            WordDocument = wordDocument;
            InitPageSize();
            InitDefaultFontInfo();
        }
        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        // Protected implementation of Dispose pattern.
        protected virtual void Dispose(bool disposing)
        {
            if (disposed)
                return;

            if (disposing)
            {
                WordDocument.Dispose();
                // Free any other managed objects here.
                //
            }

            disposed = true;
        }
        void InitPageSize()
        {
            var docPart = WordDocument.MainDocumentPart;
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
        void InitDefaultFontInfo()
        {
            if (WordDocument.MainDocumentPart.StyleDefinitionsPart != null)
            {
                var defaults = WordDocument.MainDocumentPart.StyleDefinitionsPart.Styles.Descendants<DocDefaults>().FirstOrDefault();
                if (defaults.RunPropertiesDefault.RunPropertiesBaseStyle.FontSize != null)
                {
                    DefaultFontSize = Int32.Parse(defaults.RunPropertiesDefault.RunPropertiesBaseStyle.FontSize.Val);
                    if (defaults.RunPropertiesDefault.RunPropertiesBaseStyle.RunFonts.HighAnsi != null)
                    {
                        DefaultFontName = defaults.RunPropertiesDefault.RunPropertiesBaseStyle.RunFonts.HighAnsi;
                    }
                }
            }

            const string wordmlNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
            XNamespace w = wordmlNamespace;
            StylesPart stylesPart = WordDocument.MainDocumentPart.StyleDefinitionsPart;
            if (stylesPart != null)
            {
                XDocument styleDoc = null;
                using (var reader = XmlNodeReader.Create(
                  stylesPart.GetStream(FileMode.Open, FileAccess.Read)))
                {

                    // Create the XDocument.
                    styleDoc = XDocument.Load(reader);
                    foreach (var style in styleDoc.Descendants(w + "style"))
                    {
                        var s = new Style(style.ToString());
                        if (s.Default == "1" && s.StyleRunProperties != null)
                        {
                            if (s.StyleRunProperties.FontSize != null)
                                DefaultFontSize = Int32.Parse(s.StyleRunProperties.FontSize.Val);
                            if (s.StyleRunProperties.RunFonts != null)
                                DefaultFontName = s.StyleRunProperties.RunFonts.HighAnsi;
                            break;
                        }
                    }
                }
            }
        }

        public bool NotEmptyParagraphIsInADeclarationTable(Paragraph p)
        {
            if (p.InnerText == "")
            {
                return false;
            }
            var body = WordDocument.MainDocumentPart.Document.Body;
            if  (p.Parent == body)
            {
                return false;
            }
            var cell  = p.Parent;
            if (cell == null || cell.GetType().Name != "TableCell")
            {
                return false;
            }
            var row = cell.Parent;
            if (row == null || row.Descendants<TableCell>().Count() < 5)
            {
                return false;
            }
            var table = row.Parent;
            if (table != null && table.GetType().Name == "Table" && table.Descendants<TableRow>().Count() > 1)
            {
                return true;
            }
            return false;
        }
        public string FindTitleAboveTheTable()
        {
            string title = "";
            foreach (OpenXmlPart h in WordDocument.MainDocumentPart.HeaderParts)
            {
                foreach (var p in h.RootElement.Descendants<Paragraph>())
                {
                    if (p.InnerText.Contains("PAGE"))
                    {
                        continue; // technical word info in header 
                    }
                    if (NotEmptyParagraphIsInADeclarationTable(p))
                    {
                        return title;
                    }
                    title += p.InnerText + "\n";
                }
            }
            foreach (var p in WordDocument.MainDocumentPart.Document.Descendants<Paragraph>())
            {
                if (NotEmptyParagraphIsInADeclarationTable(p))
                {
                    return title;
                }
                title += p.InnerText + "\n";
            }

            return title;
        }

    }

    public class OpenXmlWordCell : Cell
    {
        public MergedCellValues? VerticallyMerged; 
        public bool HasBottomBorder = true;
        public bool HasTopBorder = true;
        public bool HasRightBorder = true;
        public bool TableHasInsideHorizontalBorders = false;
        public OpenXmlWordCell(WordDocHolder docHolder, TableCell[] row, int cellIndexInRow, TableWidthInfo tableWidth,  
                    int rowIndexInTable, int unmergedColumnIndex, TableBorders tblBorders)
        {
            TableCell inputCell = row[cellIndexInRow];
            InitTextProperties(docHolder, inputCell);
            if (inputCell?.TableCellProperties?.TableCellBorders != null) 
            {
                var borders = inputCell.TableCellProperties.TableCellBorders;
                HasBottomBorder = borders.BottomBorder != null;
                HasTopBorder = borders.TopBorder != null;
                HasRightBorder = borders.RightBorder != null;
                if  (!HasRightBorder && cellIndexInRow + 1 < row.Length)
                {
                    HasRightBorder = row[cellIndexInRow + 1].TableCellProperties?.TableCellBorders?.LeftBorder != null;
                }
                if (!HasRightBorder && tblBorders?.InsideVerticalBorder != null && (uint)tblBorders.InsideVerticalBorder.Size > 0)
                {
                    HasRightBorder = true;
                }

            }
            var vmerge = inputCell.TableCellProperties.GetFirstChild<VerticalMerge>();
            VerticallyMerged = null;
            if (vmerge != null)
            {
                if ((vmerge.Val == null) || (vmerge.Val == MergedCellValues.Continue)) 
                {
                    // null -> MergedCellValues.Continue
                    VerticallyMerged = MergedCellValues.Continue;
                }
                else if (vmerge.Val == MergedCellValues.Restart)
                {
                    VerticallyMerged = MergedCellValues.Restart;
                }
            }
            if (tblBorders?.InsideHorizontalBorder != null && (uint)tblBorders.InsideHorizontalBorder.Size > 0)
            {
                TableHasInsideHorizontalBorders = true;
            }

            var gridSpan = inputCell.TableCellProperties.GetFirstChild<GridSpan>();
            IsMerged = gridSpan != null && gridSpan.Val > 1;
            FirstMergedRow = -1; // init afterwards
            MergedRowsCount = -1; // init afterwards

            MergedColsCount = (gridSpan == null) ? 1 : (int)gridSpan.Val;
            Row = rowIndexInTable;
            Col = unmergedColumnIndex;
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
            if (MergedRowsCount > 1)
            {
                VerticallyMerged = MergedCellValues.Restart;
                //
            }
            IsEmpty = Text.IsNullOrWhiteSpace();
            Row = cell.r;
            Col = cell.c;
        }

        static int AfterLinesCount(SpacingBetweenLines pSpc)
        {
            if (pSpc == null)
            {
                return 0;
            }
            if (pSpc.AfterLines != null && pSpc.AfterLines.HasValue)
            {
                return pSpc.AfterLines;
            }
            else if (pSpc.After != null && pSpc.After.HasValue && pSpc.Line != null && pSpc.Line.HasValue)
            {
                double linesApprox = Double.Parse(pSpc.After.Value) / Double.Parse(pSpc.Line.Value);
                return (int)Math.Round(linesApprox);
            }
            else
            {
                return 0;
            }
        }

        private void InitTextProperties(WordDocHolder docHolder, OpenXmlElement inputCell)
        {
            Text = "";
            foreach (var p in inputCell.Elements<Paragraph>())
            {
                foreach (var textOrBreak in p.Descendants())
                {
                    if (textOrBreak.LocalName == "r" && textOrBreak is Run)
                    {
                        Run r = textOrBreak as Run;
                        RunProperties rProps = r.RunProperties;
                        if (rProps != null)
                        {
                            if (rProps.FontSize != null)
                            {
                                int runFontSize = Int32.Parse(rProps.FontSize.Val);
                                if (runFontSize <= 28) FontSize = runFontSize; //  if font is too large, it is is an ocr error, ignore it
                            }
                            if (rProps.RunFonts != null)
                            {
                                FontName = rProps.RunFonts.ComplexScript;
                            }
                        }
                    }
                    else if (textOrBreak.LocalName == "t")
                    {
                        Text += textOrBreak.InnerText;
                    }
                    else if (textOrBreak.LocalName == "cr")
                    {
                        Text += "\n";
                    }
                    else if (textOrBreak.LocalName == "br")
                    /* do  not use lastRenderedPageBreak, see MinRes2011 for wrong lastRenderedPageBreak in Семенов 
                    ||
                          (textOrBreak.Name == w + "lastRenderedPageBreak") */
                    {
                        Text += "\n";
                    }
                    else if (textOrBreak.LocalName == "numPr")
                    {
                        Text += "- ";
                    }
                }
                Text += "\n";
                ParagraphProperties pPr = p.ParagraphProperties;
                if (pPr != null)
                {
                    for (int l = 0; l < AfterLinesCount(pPr.SpacingBetweenLines); ++l)
                    {
                        Text += "\n";
                    }
                }
            }
            IsEmpty = Text.IsNullOrWhiteSpace();
            if (string.IsNullOrEmpty(FontName))
            {
                FontName = docHolder.DefaultFontName;
            }
            if (FontSize == 0)
            {
                FontSize = docHolder.DefaultFontSize;
            }
            
        }
    }


    public class OpenXmlWordAdapter : IAdapter
    {
        private List<List<OpenXmlWordCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private static readonly string WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
        XmlNamespaceManager NamespaceManager;
        private int TablesCount;
        private DocxConverter _DocxConverter;

        protected static List<IAdapterScheme> _allSchemes = new List<IAdapterScheme>()
        {
            new SovetFederaciiDocxScheme(),
            // new DocxSchemePDF(),
        };

        private static Uri FixUri(string brokenUri)
        {
            return new Uri("http://broken-link/");
        }

        private void ProcessDoc(string fileName, string extension, int maxRowsToProcess)
        {
            using (var doc = new WordDocHolder(WordprocessingDocument.Open(fileName, false)))
            {
                CurrentScheme = _allSchemes.Find(x => x.CanProcess(doc.WordDocument));
                if (CurrentScheme != default)
                {
                    // CollectRows from distinct Tables
                    Title = doc.FindTitleAboveTheTable();
                    CurrentScheme.Document = doc.WordDocument.MainDocumentPart.Document;
                    TablesCount = 1;
                }
                else
                {
                    Title = doc.FindTitleAboveTheTable();
                    CollectRows(doc, maxRowsToProcess, extension);
                    UnmergedColumnsCount = GetUnmergedColumnsCountByFirstRow();
                    InitializeVerticallyMerge();
                }
            };

        }
        public OpenXmlWordAdapter(string fileName, int maxRowsToProcess)
        {
            _DocxConverter = new DocxConverter(ConvertedFileStorageUrl);
            NamespaceManager = new XmlNamespaceManager(new NameTable());
            NamespaceManager.AddNamespace("w", WordXNamespace);

            TableRows = new List<List<OpenXmlWordCell>>();

            if (fileName.EndsWith(".toloka_json"))
            {
                InitFromJson(fileName);
                UnmergedColumnsCount = GetUnmergedColumnsCountByFirstRow();
                return;
            }
            DocumentFile = fileName;
            string extension = Path.GetExtension(fileName).ToLower();
            bool removeTempFile = false;
            if (extension == ".html"
                || extension == ".htm"
                || extension == ".xhtml"
                || extension == ".pdf"
                || extension == ".doc"
                || extension == ".rtf"
                )
            {
                try
                {
                    fileName = _DocxConverter.ConvertFile2TempDocX(fileName);
                }
                catch (System.TypeInitializationException exp)
                {
                    Logger.Error("Type Exception " + exp.ToString());
                    fileName = _DocxConverter.ConvertWithSoffice(fileName);
                }
                catch (Exception exp)
                {
                    Logger.Error(String.Format("cannot convert {0} to docx, try one more time (exception: {1}", fileName, exp));
                    Thread.Sleep(10000); //10 seconds
                    fileName = _DocxConverter.ConvertFile2TempDocX(fileName);
                }
                removeTempFile = true;
            }

            try
            {
                ProcessDoc(fileName, extension, maxRowsToProcess);
            }
            catch (OpenXmlPackageException e)
            {
                // http://www.ericwhite.com/blog/handling-invalid-hyperlinks-openxmlpackageexception-in-the-open-xml-sdk/
                if (e.ToString().Contains("Invalid Hyperlink"))
                {
                    var newFileName = fileName + ".fixed.docx";
                    File.Copy(fileName, newFileName);
                    using (FileStream fs = new FileStream(newFileName, FileMode.OpenOrCreate, FileAccess.ReadWrite))
                    {
                        UriFixer.FixInvalidUri(fs, brokenUri => FixUri(brokenUri));
                    }
                    ProcessDoc(newFileName, extension, maxRowsToProcess);
                    File.Delete(newFileName);
                }
            }

            if (removeTempFile)
            {
                File.Delete(fileName);
            }
        }

        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess)
        {
            // if (OnePersonAdapter.CanProcess(fileName))
            //     // throw new SmartParserException("Impossible to parse one-person file");
            //     return new OnePersonAdapter(fileName);

            return new OpenXmlWordAdapter(fileName, maxRowsToProcess);
        }

        void CopyPortion(List<List<TJsonCell>> portion, bool ignoreMergedRows)
        {
            for (int i = 0; i < portion.Count; i++)
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

        bool HasTopBorder(int row, int column)
        {
            if (row <= 0)
            {
                return true;
            }
            int cellNo = FindMergedCellByColumnNo(TableRows, row, column);
            if (cellNo == -1)
            {
                throw new BadCellAddress(row, column);
            }
            OpenXmlWordCell cell = TableRows[row][cellNo];
            if (cell.VerticallyMerged == MergedCellValues.Continue)
            {
                return false;
            }
            if (cell.HasTopBorder)
            {
                return true;
            }
            cellNo = FindMergedCellByColumnNo(TableRows, row - 1, column);
            if (cellNo == -1)
            {
                throw new BadCellAddress(row, column); // change in column count, we hope that there is a border. Why?
            }
            var cellAbove = TableRows[row - 1][cellNo];
            if (cellAbove.HasBottomBorder)
            {
                return true;
            }
            if (!cellAbove.IsEmpty)
            {
                return false;
            }
            return cell.TableHasInsideHorizontalBorders;
        }
        int FindCellWithTopBorder(int startRow, int column)
        {
            for (int i = startRow; i > 0; --i)
            {
                try {
                    if (HasTopBorder(i, column))
                    {
                        return i;
                    }
                }
                catch (BadCellAddress e)
                {
                    return e.Row;
                }
            }
            return 0;
        }

        bool CheckBottomBorder(int row, int column, ref bool hasText)
        {
            if (row + 1 >= TableRows.Count)
            {
                return true;
            }
            int cellNo = FindMergedCellByColumnNo(TableRows, row, column);
            if (cellNo == -1)
            {
                throw new BadCellAddress(row, column);
            }
            OpenXmlWordCell cell = TableRows[row][cellNo];
            cellNo = FindMergedCellByColumnNo(TableRows, row + 1, column);
            if (cellNo == -1)
            {
                throw new BadCellAddress(row, column); // change in column count, we hope that there is a border. Why?
            }
            var cellUnder = TableRows[row + 1][cellNo];

            // если убрать это условие, сломаются тесты 10639_32.doc and 18261_22.doc 
            // и починится тест 65098_5.docx. Что делать, мне не понятно.
            hasText = hasText || !cell.IsEmpty;
            if (!cellUnder.IsEmpty && hasText)
            {
                return true;
            }


            if (cellUnder.VerticallyMerged == MergedCellValues.Continue)
            {
                return false;
            }
            if (cell.HasBottomBorder)
            {
                return true;
            }
            
            if (cellUnder.HasTopBorder)
            {
                return true;
            }
            return cell.TableHasInsideHorizontalBorders;
        }

        int FindCellWithBottomBorder(int startRow, int column)
        {
            bool hasText = false;
            for (int i = startRow; i < TableRows.Count; ++i)
            {
                try
                {
                    if (CheckBottomBorder(i, column, ref hasText))
                    {
                        return i;
                    }
                }
                catch (BadCellAddress e)
                {
                    return e.Row;
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
                        c.FirstMergedRow = FindCellWithTopBorder(c.Row, c.Col);
                        c.MergedRowsCount = FindCellWithBottomBorder(c.Row, c.Col) - c.Row + 1;
                        if (c.FirstMergedRow == c.Row) {
                            for (int i = 1; i < c.MergedRowsCount; i++)
                            {
                                int cellNo = FindMergedCellByColumnNo(TableRows, c.Row + i, c.Col);
                                if (cellNo != -1)
                                {
                                    c.Text += "\n" + TableRows[c.Row + i][cellNo].Text;
                                    TableRows[c.Row + i][cellNo].Text = "";
                                }

                            }
                        }
                    }
                    catch (Exception e)
                    {
                        Console.WriteLine(string.Format("Parsing Exception row{0} col={1}: {2}", c.Row, c.Col, e.ToString()));
                        throw;
                    }

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

        TableWidthInfo InitializeTableWidthInfo(WordDocHolder docHolder, Table table)
        {
            TableWidthInfo widthInfo = new TableWidthInfo();
            TableProperties tProp = table.GetFirstChild<TableProperties>();
            if (tProp != null)
            {
                if (tProp.TableWidth != null)
                {
                    widthInfo.TableWidthInPixels = TableWidthInfo.TryReadWidth(
                        tProp.TableWidth.Width,
                        tProp.TableWidth.Type,
                        docHolder.DocumentPageSizeInPixels);
                }

                if (tProp.TableIndentation != null)
                {
                    widthInfo.TableIndentionInPixels = TableWidthInfo.TryReadWidth(
                        tProp.TableIndentation.Width,
                        tProp.TableIndentation.Type,
                        docHolder.DocumentPageSizeInPixels);
                }
                widthInfo.TableIndentionInPixels += docHolder.DocumentPageLeftMaginInPixels;
            }
            else
            {
                widthInfo.TableWidthInPixels = docHolder.DocumentPageSizeInPixels;
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

        TableBorders GetTableBorders(Table table)
        {
            TableProperties tProp = table.GetFirstChild<TableProperties>();
            if (tProp != null)
            {
                TableBorders tBorders = tProp.GetFirstChild<TableBorders>();
                if (tBorders != null)
                {
                    return tBorders;
                } 
            }
            return null;
        }
        void ProcessWordTable(WordDocHolder docHolder, Table table, int maxRowsToProcess)
        {
            var rows = table.Descendants<TableRow>().ToList();
            TableWidthInfo widthInfo = InitializeTableWidthInfo(docHolder, table);
            int saveRowsCount = TableRows.Count;
            int maxCellsCount = 0;
            TableBorders tblBorders = GetTableBorders(table);
            for (int r = 0; r < rows.Count(); ++r)
            {
                List<OpenXmlWordCell> newRow = new List<OpenXmlWordCell>();
                int sumspan = 0;
                var tableRow = rows[r];
                int rowGridBefore = GetRowGridBefore(tableRow);
                bool isEmpty = true;
                var row = tableRow.Elements<TableCell>().ToArray();
                for (var i = 0; i < row.Length; ++i)
                {
                    var c = new OpenXmlWordCell(docHolder, row, i, widthInfo, TableRows.Count, sumspan, tblBorders);
                    if (newRow.Count == 0)
                        c.MergedColsCount += rowGridBefore;
                    if (newRow.Count > 0 && !newRow.Last().HasRightBorder)
                    {
                        newRow.Last().Text += c.Text;
                        newRow.Last().CellWidth += c.CellWidth;
                        newRow.Last().MergedColsCount += c.MergedColsCount;
                        newRow.Last().HasRightBorder = c.HasRightBorder;
                        sumspan += c.MergedColsCount;
                    }
                    else
                    {
                        newRow.Add(c);
                        sumspan += c.MergedColsCount;
                    }
                    isEmpty = isEmpty && c.IsEmpty;
                }
                if (isEmpty)
                {
                    continue;
                }
                maxCellsCount = Math.Max(newRow.Count, maxCellsCount);
                if (r == 0 && TableRows.Count > 0 &&
                    BigramsHolder.CheckMergeRow(
                        TableRows.Last().ConvertAll(x => x.Text),
                        newRow.ConvertAll(x => x.Text)))
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
            if ((TableRows.Count > 0) && !ColumnDetector.IsNamePositionAndIncomeTable(GetCells(0)))
            {
                if (maxCellsCount <= 4 || CheckNameColumnIsEmpty(TableRows, saveRowsCount))
                {
                    //remove this suspicious table 
                    TableRows.RemoveRange(saveRowsCount, TableRows.Count - saveRowsCount);
                }
            }
        }
        bool CanAppendRowsFromTable(Table table, int tableIndex)
        {
            if (table.Descendants<Table>().ToList().Count > 0)
            {
                Logger.Debug(String.Format("ignore table {0} with subtables", tableIndex));
                return false;
            }
            else if (table.InnerText.Length > 0 && !table.InnerText.Any(x => Char.IsUpper(x)))
            {
                Logger.Debug(String.Format("ignore table {0} that has no uppercase char", tableIndex));
                return false;
            }
            else if (table.InnerText.Length < 30)
            {
                Logger.Debug(String.Format("ignore table {0}, it is too short", tableIndex));
                return false;
            }
            else if (table.Descendants<TableRow>().Count() == 1)
            {
                var rows = table.Descendants<TableRow>().ToArray();
                if (TableRows.Count > 0 && TableRows.Last().Count() != rows[0].Descendants<TableCell>().Count())
                {
                    Logger.Debug(String.Format("ignore table {0}, with one row", tableIndex));
                    return false;
                }
            }
            return true;
        }

        void ProcessWordTableAndUpdateTitle(WordDocHolder docHolder, Table table, int maxRowsToProcess, int tableIndex)
        {
            if (CanAppendRowsFromTable(table, tableIndex)) { 
                ProcessWordTable(docHolder, table, maxRowsToProcess);
            }

            int debugSaveRowCount = TableRows.Count;
            if (TableRows.Count > debugSaveRowCount)
            {
                string tableText = table.InnerText.Length > 30 ? table.InnerText.Substring(0, 30) : table.InnerText;
                Logger.Debug(String.Format("add {0} rows (TableRows.Count={1} ) from table {2} Table.innertText[0:30]='{3}'",
                    TableRows.Count - debugSaveRowCount,
                    TableRows.Count,
                    tableIndex,
                    tableText));
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

        void CollectRows(WordDocHolder docHolder, int maxRowsToProcess, string extension)
        {
            var docPart = docHolder.WordDocument.MainDocumentPart;
            var tables = docPart.Document.Descendants<Table>().ToList();
            int tableIndex = 0;
            foreach (OpenXmlPart h in docPart.HeaderParts)
            {
                foreach (var t in h.RootElement.Descendants<Table>())
                {
                    ProcessWordTableAndUpdateTitle(docHolder, t, maxRowsToProcess, tableIndex);
                    tableIndex++;
                }

            }
            if (extension != ".htm" && extension != ".html") // это просто костыль. Нужно как-то встроить это в архитектуру.
                tables = ExtractSubtables(tables);

            TablesCount = tables.Count();
            foreach (var t in tables)
            {

                ProcessWordTableAndUpdateTitle(docHolder, t, maxRowsToProcess, tableIndex);
                tableIndex++;
            }

            TableRows = DropDayOfWeekRows(TableRows);
        }


        private static List<Table> ExtractSubtables(List<Table> tables)
        {
            var tablesWithDescendants = tables.Where(x => x.Descendants<Table>().Count() > 0);


            foreach (var t in tablesWithDescendants)
            {
                var extractedTables = t.Descendants<Table>().ToList();
                extractedTables = ExtractSubtables(extractedTables);
                tables = tables.Concat(extractedTables).ToList();
                foreach (var td in t.Descendants<Table>())
                {
                    td.Remove();
                }
            }

            return tables;
        }



        public override List<Cell> GetCells(int row, int maxColEnd = IAdapter.MaxColumnsCount)
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
            int cellNo = FindMergedCellByColumnNo(TableRows, row, column);
            if (cellNo == -1) return null;
            return TableRows[row][cellNo];
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