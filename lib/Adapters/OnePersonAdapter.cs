using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using DocumentFormat.OpenXml;
using System.IO;
using TI.Declarator.ParserCommon;
using AngleSharp;
using AngleSharp.Dom;
using Smart.Parser.Lib.Adapters.HtmlSchemes;
using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Smart.Parser.Lib.Adapters.DocxSchemes;

namespace Smart.Parser.Adapters
{
    public class OnePersonAdapter : IAdapter
    {
 
        #region consts
        protected const string NAME_COLUMN = "ФИО";
        protected const string COLUMN_INCOME = "Доход";
        protected const string REAL_ESTATE_TYPE = "Вид недвижимости в собственности";
        protected const string REAL_ESTATE_SQUARE = "Площадь в собственности (кв.м)";
        protected const string REAL_ESTATE_COUTRY = "Страна расположения имущества в собственности";
        protected const string STATE_ESTATE_TYPE = "Вид недвижимости в пользовании";
        protected const string STATE_ESTATE_SQUARE = "Площадь в пользовании (кв.м)";
        protected const string STATE_ESTATE_COUTRY = "Страна расположения имущества в пользовании";
        protected const string VEHICLES_TYPE = "Транспортные средства, вид";
        protected const string VEHICLES_NAME = "Транспортные средства, марка";

        protected static List<IDocxScheme> _allSchemes = new List<IDocxScheme>()
        {
            new DocxScheme1(),
            new DocxSchemePDF()
        };
        #endregion

        #region fields
        protected List<WorksheetInfo> _worksheets;
        protected int _worksheetIndex;
        protected IDocxScheme _scheme;
        protected List<List<Cell>> _table;
        #endregion

        #region properties
        public WorksheetInfo Worksheet { get => _worksheets[_worksheetIndex]; }
        #endregion

        public OnePersonAdapter(string fileName)
        {
            this.DocumentFile = fileName;
            using (var document = WordprocessingDocument.Open(fileName, false))
            {
                _scheme = _allSchemes.Find(x => x.CanProcess(document));
                _scheme.Document = document;
                _worksheets = new List<WorksheetInfo>(1);
                var worksheet = new WorksheetInfo();
                MakeTable(document, worksheet);
                _worksheets.Add(worksheet);
            }
        }
        
        public static bool CanProcess(string fileName)
        {
            var document = WordprocessingDocument.Open(fileName, false);
            return _allSchemes.Any(x=> x.CanProcess(document));
        }

        protected void MakeTable(WordprocessingDocument document, WorksheetInfo worksheet)
        {
            _table = GetTable(document, out var name, out var title);
            worksheet.PersonName = name;
            worksheet.Table = _table;
            worksheet.Title = title;

            _scheme.ProcessMainPerson(name, this);
        }

        protected  List<List<Cell>> GetTable(WordprocessingDocument document, out string name,  out string title)
        {
            title = _scheme.GetTitle();
            name = _scheme.GetPersonName();

            var table = new List<List<Cell>>();
            table.Add(MakeHeaders(1).ToList());
            table.Insert(0, GetTitleRow(title, table));
            
            return table;
        }

        private static List<Cell> GetTitleRow(string title, List<List<Cell>> table)
        {
            List<Cell> titleRow = new List<Cell>();
            var titleCell = new Cell
            {
                IsMerged = true,
                Text = title,
                Row = 0,
                Col = 0,
                MergedColsCount = table[0].Count,
                MergedRowsCount = 1
            };
            titleRow.Add(titleCell);
            return titleRow;
        }
        
        protected IEnumerable<Cell> MakeHeaders(int rowNum)
        {

            List<string> headerLine = new List<string>
            {
                NAME_COLUMN,
                COLUMN_INCOME,
                REAL_ESTATE_TYPE,
                REAL_ESTATE_SQUARE,
                REAL_ESTATE_COUTRY,
                STATE_ESTATE_TYPE,
                STATE_ESTATE_SQUARE,
                STATE_ESTATE_COUTRY,
                VEHICLES_NAME,
                VEHICLES_TYPE,
            };
            return GetRow(headerLine, rowNum);
        }

        public void AddRow(List<string> line)
        {
            int rowNum = _table.Count;
            _table.Insert(rowNum, GetRow(line, rowNum).ToList());
        }
        
        protected static Cell GetCell(string text, int row, int column)
        {
            Cell cell = new Cell
            {
                Text = text,
                Row = row,
                Col = column,
                IsMerged = false,
                CellWidth = 1
            };
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
        
        public override bool IsExcel()
        {
            return false;
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
