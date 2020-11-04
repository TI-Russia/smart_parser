using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using TI.Declarator.ParserCommon;
using AngleSharp;
using AngleSharp.Dom;
using Parser.Lib;
using System.Text;

namespace Smart.Parser.Adapters
{
    class HtmlDocHolder
    {
        public IDocument HtmlDocument;
        public int DefaultFontSize = 10;
        public string DefaultFontName = "Times New Roman";
        public int DocumentPageSizeInPixels;
        public HtmlDocHolder(IDocument htmlDocument)
        {
            HtmlDocument = htmlDocument;
            DocumentPageSizeInPixels = 1000;
        }
        
        public string FindTitleAboveTheTable()
        {
            var title = new StringBuilder();
            bool foundTable = false;
            var addedLines = new HashSet<string>();
            foreach (var p in HtmlDocument.All.ToList() )
            {
                if (p.TextContent.IsNullOrWhiteSpace()) continue;
                if (p.TextContent.Length > 300) continue;
                if (addedLines.Contains(p.TextContent)) continue;
                addedLines.Add(p.TextContent);
                if (p.LocalName == "h1" || p.LocalName == "h2")
                {
                    title.Append(p.TextContent).Append(' ');
                }
                else if ((p.LocalName == "p" || p.LocalName == "div" || p.LocalName == "span") && p.TextContent.IndexOf("декабря") != -1)
                {
                    title.Append(p.TextContent).Append(' ');
                }
                else
                {
                    if (p.LocalName == "table")
                    {
                        foundTable = true;
                    }
                    if (!foundTable)
                    {
                        if (p.LocalName == "p")
                        {
                            title.Append(p.TextContent).Append(' ');
                        }
                    }
                }
            }
            return title.ToString();
        }

    }

    public class MyMarkupFormatter : IMarkupFormatter
    {
        String IMarkupFormatter.Comment(IComment comment)
        {
            return String.Empty;
        }

        String IMarkupFormatter.Doctype(IDocumentType doctype)
        {
            return String.Empty;
        }

        String IMarkupFormatter.Processing(IProcessingInstruction processing)
        {
            return String.Empty;
        }

        String IMarkupFormatter.Text(ICharacterData text)
        {
            return text.Data;
        }

        String IMarkupFormatter.OpenTag(IElement element, Boolean selfClosing)
        {
            switch (element.LocalName)
            {
                case "p":
                    return "\n\n";
                case "br":
                    return "\n";
                case "span":
                    return " ";
            }

            return String.Empty;
        }

        String IMarkupFormatter.CloseTag(IElement element, Boolean selfClosing)
        {
            return String.Empty;
        }

        String IMarkupFormatter.Attribute(IAttr attr)
        {
            return String.Empty;
        }
    }
    
    class HtmlAdapterCell : Cell
    {
        public HtmlAdapterCell(int row, int column)
        {
            Row = row;
            Col = column;
            Text = "";
            IsEmpty = true;
            CellWidth = 0;
            MergedRowsCount = 1;
            MergedColsCount = 1;
        }

        public HtmlAdapterCell(HtmlDocHolder docHolder, IElement inputCell, int row, int column)
        {
            InitTextProperties(docHolder, inputCell);
            FirstMergedRow = row;
            MergedRowsCount = 1; 
            MergedColsCount = 1;
            Row = row;
            Col = column;
            IsMerged = false;
            IsEmpty = Text.IsNullOrWhiteSpace();
            if (inputCell.HasAttribute("colspan"))
            {
                int v;
                if ( Int32.TryParse(inputCell.GetAttribute("colspan"), out v))
                {
                    MergedColsCount = v;
                    IsMerged = MergedColsCount > 1;
                }
            }
            if (inputCell.HasAttribute("rowspan"))
            {
                int v;
                if (Int32.TryParse(inputCell.GetAttribute("rowspan"), out v))
                {
                    MergedRowsCount = v;
                }
            }
            if (inputCell.HasAttribute("width"))
            {
                string s = inputCell.GetAttribute("width");
                double width;
                if (s.EndsWith("%") && double.TryParse(s.Substring(0, s.Length-1), out width))
                {
                    CellWidth = (int)( (double)docHolder.DocumentPageSizeInPixels * (width / 100.0) ) ;
                }
                if (double.TryParse(s, out width))
                {
                    CellWidth = (int)width;
                }
                else
                {
                    CellWidth = 50;
                }
            }

        }


        public HtmlAdapterCell(IAdapter.TJsonCell cell)
        {
            Text = cell.t;
            MergedColsCount = cell.mc;
            MergedRowsCount = cell.mr;
            IsEmpty = Text.IsNullOrWhiteSpace();
            Row = cell.r;
            Col = cell.c;
        }

        private void InitTextProperties(HtmlDocHolder docHolder, IElement inputCell)
        {
            FontName = "";
            FontSize = 0;
            var myFormatter = new MyMarkupFormatter();
            //var myFormatter = new AngleSharp.Html.PrettyMarkupFormatter();
            Text = inputCell.ToHtml(myFormatter);
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

    public class AngleHtmlAdapter : IAdapter
    {
        private List<List<HtmlAdapterCell>> TableRows;
        private string Title;
        private int UnmergedColumnsCount;
        private int TablesCount;

        public static IDocument GetAngleDocument(string filename)
        {
            //string text = File.ReadAllText(filenameS);
            var config = Configuration.Default;
            using (FileStream fileStream = File.Open(filename, FileMode.Open))
            {
                var context = BrowsingContext.New(config);
                var task = context.OpenAsync(req => req.Content(fileStream));
                task.Wait();
                var document = task.Result;
                return document;
            }
        }

        public AngleHtmlAdapter(string fileName, int maxRowsToProcess)
        {
            TableRows = new List<List<HtmlAdapterCell>>();
            DocumentFile = fileName;
            var holder = new HtmlDocHolder(GetAngleDocument(fileName));
            Title = holder.FindTitleAboveTheTable();
            CollectRows(holder, maxRowsToProcess);
            UnmergedColumnsCount = GetUnmergedColumnsCountByFirstRow();
        }

        public static IAdapter CreateAdapter(string fileName, int maxRowsToProcess)
        {
            return new AngleHtmlAdapter(fileName, maxRowsToProcess);
        }

        public override string GetTitleOutsideTheTable()
        {
            return Title;
        }

        List<IElement> GetHtmlTableRows(IElement htmltable)
        {
            return htmltable.QuerySelectorAll("*").Where(m => m.LocalName == "tr").ToList();
        }

        List<IElement> GetHtmlTableCells(IElement htmlTableRow)
        {
            return htmlTableRow.QuerySelectorAll("*").Where(m => m.LocalName == "td" || m.LocalName == "th").ToList();
        }

        void InsertRowSpanCells(int start, int end)
        {
            if (start + 1 >= end) return;
            for( ;start < end; ++start) 
            {
                var firstLine = TableRows[start];
                for (int cellIndex = 0; cellIndex < firstLine.Count; ++cellIndex)
                {
                    if (firstLine[cellIndex].MergedRowsCount > 1 && firstLine[cellIndex].FirstMergedRow == start)
                    {
                        for (int rowIndex = start + 1; rowIndex < start + firstLine[cellIndex].MergedRowsCount; ++rowIndex)
                        {
                            if (rowIndex >= TableRows.Count)
                            {
                                break; // #-max-rows 100
                            }
                            var additCell = new HtmlAdapterCell(rowIndex, cellIndex);
                            additCell.FirstMergedRow = start;
                            additCell.MergedRowsCount = firstLine[cellIndex].MergedRowsCount - rowIndex;
                            additCell.CellWidth = firstLine[cellIndex].CellWidth;
                            if  (cellIndex < TableRows[rowIndex].Count)
                                TableRows[rowIndex].Insert(cellIndex, additCell);
                            else
                                TableRows[rowIndex].Add(additCell);
                            for (int afterCellIndex = cellIndex + 1; afterCellIndex < TableRows[rowIndex].Count; ++afterCellIndex)
                            {
                                TableRows[rowIndex][afterCellIndex].Col += firstLine[cellIndex].MergedColsCount;
                            }
                        }
                    }
                }
            }
        }


        void ProcessHtmlTable(HtmlDocHolder docHolder, IElement table, int maxRowsToProcess)
        {
            var rows = GetHtmlTableRows(table);
            int saveRowsCount = TableRows.Count;
            int maxCellsCount = 0;
            int maxSumSpan = 0;
            for (int r = 0; r < rows.Count(); ++r)
            {
                List<HtmlAdapterCell> newRow = new List<HtmlAdapterCell>();
                int sumspan = 0;
                var row = rows[r];
                bool isEmpty = true;
                foreach (var rowCell in GetHtmlTableCells(rows[r]))
                {
                    var c = new HtmlAdapterCell(docHolder, rowCell, TableRows.Count, sumspan);
                    newRow.Add(c);
                    for (int k = 1; k < c.MergedColsCount; ++k)
                    {
                        newRow.Add(new HtmlAdapterCell(TableRows.Count, sumspan + k));
                    }
                    sumspan += c.MergedColsCount;
                    isEmpty = isEmpty && c.IsEmpty;
                }
                if (isEmpty)
                {
                    continue;
                }
                maxCellsCount = Math.Max(newRow.Count, maxCellsCount);
                maxSumSpan = Math.Max(sumspan, maxSumSpan);
                
                // see 7007_8.html in tests
                for (int k = sumspan; k < maxSumSpan; ++k)
                {
                    newRow.Add(new HtmlAdapterCell(TableRows.Count, sumspan + k));
                }

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
            if (saveRowsCount < TableRows.Count)
            {
                if (maxCellsCount <=  4)
                {
                    //remove this suspicious table 
                    TableRows.RemoveRange(saveRowsCount, TableRows.Count - saveRowsCount);
                }
                else
                {
                    InsertRowSpanCells(saveRowsCount, TableRows.Count);
                    if (CheckNameColumnIsEmpty(TableRows, saveRowsCount))
                    {
                        TableRows.RemoveRange(saveRowsCount, TableRows.Count - saveRowsCount);
                    }
                }
            }
        }

        void ProcessHtmlTableAndUpdateTitle(HtmlDocHolder docHolder, IElement table, int maxRowsToProcess, int tableIndex)
        {
            int debugSaveRowCount = TableRows.Count;
            if (table.QuerySelectorAll("*").Where(m => m.LocalName=="table").ToList().Count > 0)
            {
                Logger.Debug(String.Format("ignore table {0} with subtables", tableIndex));
            }
            else if (table.TextContent.Length > 0 && !table.TextContent.Any(x => Char.IsUpper(x)))
            {
                Logger.Debug(String.Format("ignore table {0} that has no uppercase char", tableIndex));
            }
            else if (table.TextContent.Length < 30)
            {
                Logger.Debug(String.Format("ignore table {0}, it is too short", tableIndex));

            }
            else
            {
                ProcessHtmlTable(docHolder, table, maxRowsToProcess);
            }
            if (TableRows.Count > debugSaveRowCount)
            {
                string tableText = table.TextContent.Length > 30 ? table.TextContent.Substring(0, 30).ReplaceEolnWithSpace() : table.TextContent.ReplaceEolnWithSpace();
                Logger.Debug(String.Format("add {0} rows (TableRows.Count={1} ) from table {2} Table.innertText[0:30]='{3}'",
                    TableRows.Count - debugSaveRowCount,
                    TableRows.Count,
                    tableIndex,
                    tableText));
            }
            if (Title.Length == 0 && table.TextContent.Length > 30 && table.TextContent.ToLower().IndexOf("декабря") != -1)
            {
                var rows = new List<String>();
                foreach (var r in GetHtmlTableRows(table))
                {
                    rows.Add(r.TextContent);
                }
                Title = String.Join("\n", rows);
            }
        }

        void CollectRows(HtmlDocHolder docHolder, int maxRowsToProcess)
        {
            var tables = docHolder.HtmlDocument.QuerySelectorAll("*").Where(m => m.LocalName == "table").ToList();
            int tableIndex = 0;
            TablesCount = tables.Count();
            foreach (var t in tables)
            {
                ProcessHtmlTableAndUpdateTitle(docHolder, t, maxRowsToProcess, tableIndex);
                tableIndex++;
            }
            TableRows = DropDayOfWeekRows(TableRows); 
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
            int cellNo = FindMergedCellByColumnNo<HtmlAdapterCell>(TableRows, row, column);
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
