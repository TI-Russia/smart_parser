using SmartParser.Lib;
using StringHelpers;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using DocumentFormat.OpenXml;
using System.IO;
using AngleSharp;
using AngleSharp.Dom;
using System.Text.RegularExpressions;

namespace SmartParser.Lib
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
        protected const string REAL_ESTATE_CAPTION = "Вид недвижимости в собственности";
        protected const string REAL_ESTATE_SQUARE = "Площадь в собственности (кв.м)";
        protected const string REAL_ESTATE_OWNERSHIP = "Вид собственности";
        protected static List<IHtmlScheme> _allSchemes = new List<IHtmlScheme>()
            {
                new ArbitrationCourt1(),
                new ArbitrationCourt2(),
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
            using (IDocument document = AngleHtmlAdapter.GetAngleDocument(filename))
            {
                _scheme = _allSchemes.Find(x => x.CanProcess(document));
                _scheme.Document = document;
                MakeWorksheets(document);
                _scheme.Document = null; // free
            }
        }


        private void MakeWorksheets(IDocument document)
        {
            _worksheetIndex = 0;
            List<int> years = _scheme.GetYears();
            if (years.Count > 0)
            {
                MakeWorksheetWithYears(document, years);
            }
            else
            {
                MakeWorksheetWithoutYears(document);
            }
        }


        private void MakeWorksheetWithoutYears(IDocument document)
        {
            _worksheets = new List<WorksheetInfo>(1);
            var worksheet = new WorksheetInfo();
            MakeTable(document, worksheet);
            _worksheets.Add(worksheet);
        }


        private void MakeWorksheetWithYears(IDocument document, List<int> years)
        {
            _worksheets = new List<WorksheetInfo>(years.Count);
            foreach (var year in years)
            {
                var currWorksheet = new WorksheetInfo();
                MakeTable(document, currWorksheet, year.ToString());
                _worksheets.Add(currWorksheet);
            }
        }



        protected  void MakeTable(IDocument document, WorksheetInfo worksheet, string year = null)
        {
            
            List<List<Cell>> table = GetTable(document, year, out var name, out var title);
            worksheet.PersonName = name;
            worksheet.Table = table;
            worksheet.Year = year;
            worksheet.Title = title;
        }



        protected  List<List<Cell>> GetTable(IDocument document,  string year, out string name,  out string title)
        {
            name = _scheme.GetPersonName();
            title = _scheme.GetTitle( year);
            var members = _scheme.GetMembers( name, year);

            List<List<Cell>> table = new List<List<Cell>>();

            table.Add(MakeHeaders(members.First(), 1).ToList());
            ProcessMainMember(table, members.Skip(0).First(), name);
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
                var name = _scheme.GetMemberName(memberElement);
                var tableLines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
                _scheme.ModifyLinesForAdditionalFields(tableLines);

                for (int i = 1; i < tableLines.Count(); i++)
                {
                    List<Cell> line = new List<Cell>();
                    line.Add(GetCell(name, table.Count, 0));
                    //ModifyLinesForRealEstate(tableLines);
                    line.AddRange(GetRow(tableLines[i], table.Count, 1));
                    table.Add(line);
                }
            }
        }

        protected void ProcessMainMember(List<List<Cell>> table, IElement memberElement, string name)
        {
            var tableLines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
            _scheme.ModifyLinesForAdditionalFields(tableLines, true);
            foreach (var tableLine in tableLines.Skip(1))
            {
                List<Cell> line = new List<Cell>();
                table.Add(line);
                if (table.Count > 2) 
                    name = ""; 
                line.Add(GetCell(name, table.Count, 0));
                line.AddRange(GetRow(tableLine, table.Count, 1));
            }
        }


        protected IEnumerable<Cell> MakeHeaders( IElement memberElement, int rowNum)
        {

            List<List<string>> lines = ExtractLinesFromTable(_scheme.GetTableFromMember(memberElement));
            var headerLine = lines[0];
            _scheme.ModifyHeaderForAdditionalFields(headerLine);
            headerLine.Insert(0, NAME_COLUMN_CAPTION);
            return GetRow(headerLine, rowNum);
        }


        protected static List<List<string>> ExtractLinesFromTable(IElement tableElement)
        {
            List<List<string>> lines = new List<List<string>>();
            var linesSelection = tableElement.QuerySelectorAll("tr");
            foreach(var lineElement in linesSelection)
            {
                var splitedCellsLine = new List<List<string>>();
                foreach(var cell in lineElement.Children)
                {
                    var splitted = new List<string>();
                    var current = "";
                    
                    foreach (var child in cell.ChildNodes)
                    {
                        if (child.NodeName == "BR")  {
                            splitted.Add(current);
                            current = "";
                        } else if (child.NodeName == "P") {
                            splitted.Add(child.TextContent.Replace("\n", " ").Replace("\t", "").Trim());
                        } else  {
                            current += child.TextContent.Replace("\n", " ").Replace("\t", "").Trim();
                        }
                    }
                    splitted.Add(current);
                    splitedCellsLine.Add(splitted);
                }

                var finish = false;
                while (!finish)
                {
                    finish = true;
                    var line = new List<string>();
                    foreach (var cellList in splitedCellsLine)
                    {
                        if (cellList.Any())
                        {
                            finish = false;
                            var item = cellList[0];
                            cellList.RemoveAt(0);
                            line.Add(item);
                        }
                        else
                        {
                            line.Add("");
                        }
                    }
                    if (finish) break;
                    lines.Add(line);
                }
            }
            return lines;
        }


        public static bool CanProcess(string filename)
        {
            var document = AngleHtmlAdapter.GetAngleDocument(filename);
            return _allSchemes.Any(x=>x.CanProcess(document));
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
        public override List<Cell> GetUnmergedRow(int row)
        {
            throw new Exception("unimplemented method");
        }
        #endregion
    }
}
