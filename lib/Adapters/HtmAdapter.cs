using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using DocumentFormat.OpenXml;
using System.IO;
using TI.Declarator.ParserCommon;
using AngleSharp;
using AngleSharp.Html.Parser;
using AngleSharp.Dom;
using Smart.Parser.Lib.Adapters.HtmlSchemes;

namespace Smart.Parser.Adapters
{
    public class WorksheetInfo
    {
        private string personName;
        private string year;
        private string title;
        private List<List<Cell>> table;

        public WorksheetInfo()
        {
        }

        public WorksheetInfo(string personName, string year, string title, List<List<Cell>> table)
        {
            PersonName = personName;
            Year = year;
            Title = title;
            Table = table;
        }

        public string PersonName { get => personName; set => personName = value; }
        public string Year { get => year; set => year = value; }
        public string Title { get => title; set => title = value; }
        public List<List<Cell>> Table { get => table; set => table = value; }

      
    }


    public class HtmAdapter : IAdapter
    {
 
        #region consts
        protected const string NAME_COLUMN_CAPTION = "ФИО";
        protected static List<IHtmlScheme> _allSchemes = new List<IHtmlScheme>()
            {
                new ArbitrationCourt1(),
            };

        #endregion

        #region fields
        protected List<WorksheetInfo> _worksheets;
        protected int _worksheetIndex;
        protected IHtmlScheme _scheme;
        #endregion

        #region properties
        public WorksheetInfo Worksheet { get => _worksheets[_worksheetIndex]; }
        #endregion

        public HtmAdapter(string filename)
        {
            this.DocumentFile = filename;
            var text = File.ReadAllText(filename);
            using (IDocument document = GetDocument(text))
            {
                _scheme = _allSchemes.Find(x => x.CanProcess(document));
                MakeWorksheets(document);
            }
        }

        private void MakeWorksheets(IDocument document)
        {
            List<int> years = _scheme.GetYears(document);
            _worksheets = new List<WorksheetInfo>(years.Count);
            _worksheetIndex = 0;
            foreach(var year in years)
            {
                var currWorksheet = new WorksheetInfo();
                MakeTable(document, currWorksheet, year.ToString());
                _worksheets.Add(currWorksheet);
            }
        }

        protected  void MakeTable(IDocument document, WorksheetInfo worksheet, string year)
        {
            List<List<Cell>> table = GetTable(document, year, out var name, out var title);
            worksheet.PersonName = name;
            worksheet.Table = table;
            worksheet.Year = year;
            worksheet.Title = title;
        }



        protected  List<List<Cell>> GetTable(IDocument document,  string year, out string name,  out string title)
        {
            name = _scheme.GetPersonName(document);
            title = _scheme.GetTitle(document, year);
            var members = _scheme.GetMembers(document, name, year);

            List<List<Cell>> table = new List<List<Cell>>();


            table.Add(MakeHeaders(members.First(), 1).ToList());
            table.Add(GetMainMember(members.First(), name, 2));
            ProcessAdditionalMembers(table, members.Skip(1), name);
            table.Insert(0, GetTitleRow(title, table));
            return table;


        }

        private static List<Cell> GetTitleRow(string title, List<List<Cell>> table)
        {
            List<Cell> titleRow = new List<Cell>();
            var titleCell = new Cell();
            titleCell.IsMerged = true;
            titleCell.Text = title;
            titleCell.Row = 0;
            titleCell.Col = 0;
            titleCell.MergedColsCount = table[1].Count;
            titleCell.MergedRowsCount = 1;
            titleRow.Add(titleCell);
            return titleRow;
        }

        protected void ProcessAdditionalMembers(List<List<Cell>> table, IEnumerable<IElement> members, string declarantName)
        {
            
            foreach(var memberElement in members)
            {
                List<Cell> line = new List<Cell>();
                //var name = memberElement.QuerySelectorAll("h2.income-member").First().Text();
                var name = _scheme.GetMemberName(memberElement);
                string tmpName = name.ToLower();
                if (
                    tmpName == "несовершеннолетние дети" ||
                    tmpName == "несовершеннолетний ребенок" ||
                    tmpName == "супруг" ||
                    tmpName == "супруга"
                    )
                    name = $"{tmpName} {declarantName}";
                line.Add(GetCell(name, table.Count, 0));
                //var tableLines = ExtractLinesFromTable(memberElement.QuerySelectorAll("table").First());
                var tableLines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
                line.AddRange(GetRow(tableLines[1], table.Count, 1));

                table.Add(line);
            }
        }

       

        protected  List<Cell> GetMainMember(IElement memberElement, string name, int rowNum)
        {
            List<Cell> line = new List<Cell>();
            line.Add(GetCell(name, rowNum, 0));
            //var tableLines = ExtractLinesFromTable(tableElement.Children.First());
            var tableLines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
            line.AddRange(GetRow(tableLines[1], rowNum, 1));
            return line;
        }


        protected IEnumerable<Cell> MakeHeaders( IElement memberElement, int rowNum)
        {
            
            //List<List<string>> lines = ExtractLinesFromTable(element.Children.First());
            List<List<string>> lines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
            var headerLine = lines[0];

            headerLine.Insert(0, NAME_COLUMN_CAPTION);
            return GetRow(headerLine, rowNum);
        }



        protected static List<List<string>> ExtractLinesFromTable(IElement tableElement)
        {
            List<List<string>> lines = new List<List<string>>();
            var linesSelection = tableElement.QuerySelectorAll("tr");
            foreach(var lineElement in linesSelection)
            {
                List<string> line = new List<string>();
                foreach(var cell in lineElement.Children)
                {
                    var raw = cell.TextContent;
                    raw = raw.Replace("\n", "").Replace("\t", "");
                    line.Add(raw);
                }
                lines.Add(line);
            }
            return lines;
        }



        public static bool CanProcess(string filename)
        {
            string text = File.ReadAllText(filename);
            var document = GetDocument(text);
            return _allSchemes.Any(x=>x.CanProcess(document));
            
            //GetTitle(document, "");
            //return title.Contains("Арбитражный суд города Москвы");
        }



        protected static IDocument GetDocument(string text)
        {
            var config = Configuration.Default;

            var context = BrowsingContext.New(config);
            var task = context.OpenAsync(req => req.Content(text));
            task.Wait();
            var document = task.Result;
            return document;
        }

        protected static Cell GetCell(string text, int row, int column)
        {
            Cell cell = new Cell();
            cell.Text = text;
            cell.Row = row;
            cell.Col = column;
            cell.IsMerged = false;
            cell.CellWidth = 1;
            return cell;
        }

        private static IEnumerable<Cell> GetRow(List<string> tableLine, int row, int columnShift = 0)
        {
            return tableLine.Select((x, i) => GetCell(x, row, i + columnShift));
        }


        #region IAdapter
        public override Cell GetCell(int row, int column)
        {
            Cell cell = Worksheet.Table[row][column];
            return cell;
        }

      
        public override int GetColsCount()
        {
            return Worksheet.Table[1].Count;
        }

        public override int GetRowsCount()
        {
            return Worksheet.Table.Count ;
        }


        public override bool Equals(object obj)
        {
            return base.Equals(obj);
        }

        public override int GetHashCode()
        {
            return base.GetHashCode();
        }

        public override string ToString()
        {
            return base.ToString();
        }

        public override bool IsExcel()
        {
            return false;
        }

        public override string GetDocumentPosition(int row, int col)
        {
            return base.GetDocumentPosition(row, col);
        }

        public override List<Cell> GetCells(int row, int maxColEnd = 1024)
        {
            return Worksheet.Table[row];
        }

        public override Cell GetDeclarationFieldWeak(ColumnOrdering columnOrdering, int row, DeclarationField field, out TColumnInfo colSpan)
        {
            return base.GetDeclarationFieldWeak(columnOrdering, row, field, out colSpan);
        }

        public override string GetTitleOutsideTheTable()
        {
            return Worksheet.Title;
        }

        public override int GetWorkSheetCount()
        {
            return _worksheets.Count;
        }

        public override int GetTablesCount()
        {
            return 1;
        }

        public override void SetCurrentWorksheet(int sheetIndex)
        {
            _worksheetIndex = sheetIndex;
        }

        public override string GetWorksheetName()
        {
            return base.GetWorksheetName();
        }

        public override int? GetWorksheetIndex()
        {
            return _worksheetIndex;
        }
        #endregion
    }
}
