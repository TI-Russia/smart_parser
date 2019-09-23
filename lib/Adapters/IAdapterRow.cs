using Parser.Lib;
using static Parser.Lib.SmartParserException;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Smart.Parser.Lib;
using TI.Declarator.ParserCommon;


namespace Smart.Parser.Adapters
{
    public class Cell 
    {
        public virtual bool IsMerged { set; get; } = false;
        public virtual int FirstMergedRow { set; get; } = -1;
        public virtual int MergedRowsCount { set; get; } = -1;
        public virtual int MergedColsCount { set; get; } = 1;
        public virtual bool IsEmpty { set; get; } = true;
        public virtual string Text { set; get; } = "";

        public virtual string GetText(bool trim = true)
        {
            var text = Text;
            if (trim)
            {
                char[] spaces = { ' ', '\n', '\r', '\t' };
                text = text.CoalesceWhitespace().Trim(spaces);
            }

            return text;
        }
        public virtual string GetTextOneLine()
        {
            return Text.Replace("\n", " ").Trim();
        }

        public int Row { get; set; } = -1;
        public int Col { get; set; } = -1;

        public int CellWidth = 0;
    };

    public class DataRow : DataRowInterface
    {
        static readonly DeclarationField[] IntFieldsArray = new DeclarationField[] {
            DeclarationField.Number,
            DeclarationField.MixedRealEstateSquare,
            DeclarationField.OwnedRealEstateSquare,
            DeclarationField.StatePropertySquare,
            DeclarationField.DeclaredYearlyIncome,
            DeclarationField.DeclaredYearlyIncomeThousands
        };
        static readonly HashSet<DeclarationField> IntegerFields = new HashSet<DeclarationField>(IntFieldsArray);

        static readonly DeclarationField[] CountryFieldsArray = new DeclarationField[] {
            DeclarationField.MixedRealEstateCountry,
            DeclarationField.OwnedRealEstateCountry,
            DeclarationField.StatePropertyCountry,
            DeclarationField.StatePropertySquare
        };
        static readonly HashSet<DeclarationField> CountryFields = new HashSet<DeclarationField>(CountryFieldsArray);

        public DataRow(IAdapter adapter, ColumnOrdering columnOrdering, int row)
        {
            this.row = row;
            this.adapter = adapter;
            this.ColumnOrdering = columnOrdering;
            Cells = adapter.GetCells(row);
            MappedHeader = MapByOrderAndIntersection(columnOrdering, Cells);
            if (MappedHeader == null )
            {
                MappedHeader = MapByMaxIntersection(columnOrdering, Cells);
            }
            
        }
        static bool TestFieldSemantics(DeclarationField field, Cell cell)
        {
            if (cell.IsEmpty) return false;
            string text = cell.GetText(true);
            if (IntegerFields.Contains(field) )
            {
                if (Char.IsNumber(text[0]))
                    return true;
            }
            else  if (CountryFields.Contains(field))
            {
                if (DataHelper.IsCountryStrict(text))
                {
                    return true;
                }
            }
            return false;

        }

        static Dictionary<DeclarationField, Cell> MapByOrderAndIntersection(ColumnOrdering columnOrdering, List<Cell> cells)
        {
            if (columnOrdering.MergedColumnOrder.Count != cells.Count)
            {
                return null;
            }
            int start = 0;
            var res = new Dictionary<DeclarationField, Cell>();
            for (int i = 0; i < cells.Count; i++)
            {
                int s1 = start;
                int e1 = start + cells[i].CellWidth;
                var colInfo = columnOrdering.MergedColumnOrder[i];
                int s2 = colInfo.ColumnPixelStart;
                int e2 = colInfo.ColumnPixelStart + colInfo.ColumnPixelWidth;
                if (ColumnOrdering.PeriodIntersection(s1, e1, s2, e2) == 0)
                {
                    if (!TestFieldSemantics(colInfo.Field, cells[i]))
                    {
                        return null;
                    }
                }
                res[columnOrdering.MergedColumnOrder[i].Field] = cells[i];

                start = e1;
            }
            return res;

        }

        static Dictionary<DeclarationField, Cell> MapByMaxIntersection(ColumnOrdering columnOrdering, List<Cell> cells)
        {
            var res = new Dictionary<DeclarationField, Cell>();
            int start = 0;
            foreach (var c in cells)
            {
                if (c.CellWidth > 0)
                {
                    var field = columnOrdering.FindByPixelIntersection(start, start + c.CellWidth);
                    if (field == DeclarationField.None)
                    {
                        return null;
                    }
                    start += c.CellWidth;
                }
            }
            return res;
        }

        public bool IsEmpty(params DeclarationField[] fields)
        {
            return fields.All(field => GetContents(field, false).IsNullOrWhiteSpace());
        }

        public int GetRowIndex()
        {
            return Cells[0].Row;
        }

        public void Merge(DataRow other)
        {
            for (int i = 0; i < Cells.Count(); i++)
            {
                Cells[i].Text += " " + other.Cells[i].Text;
            }
        }

        public Cell GetDeclarationField(DeclarationField field)
        {
            Cell cell;
            if (MappedHeader != null && MappedHeader.TryGetValue(field, out cell))
            {
                return cell;
            }
            return adapter.GetDeclarationFieldWeak(ColumnOrdering, row, field);
        }

        public string GetContents(DeclarationField field, bool except = true)
        {
            if (!ColumnOrdering.ContainsField(field))
            {
                if (!except)
                    return "";
            }
            var c = GetDeclarationField(field);
            if (c == null)
            {
                return "";
            }
            return c.GetText(true);
        }

        public bool IsEmpty()
        {
            return Cells.All(cell => cell.Text.IsNullOrWhiteSpace());
        }

        public int? GetPersonIndex()
        {
            int? index = null;
            if (this.ColumnOrdering.ContainsField(DeclarationField.Number))
            {
                string indexStr = GetDeclarationField(DeclarationField.Number).Text
                    .Replace(".", "").CleanWhitespace();
                int indVal;
                bool dummyRes = Int32.TryParse(indexStr, out indVal);
                if (dummyRes)
                {
                    index = indVal;
                }
            }
            return index;
        }

        void SetRelative(string value)
        {
            RelativeType = value;
            if (RelativeType != String.Empty && !DataHelper.IsRelativeInfo(RelativeType))
            {
                throw new SmartParserException(
                    string.Format("Wrong relative type {0} at row {1}", RelativeType, GetRowIndex()));
            }
        }
        void DivideNameAndOccupation()
        {
            var nameCell = GetDeclarationField(DeclarationField.NameAndOccupationOrRelativeType);
            NameDocPosition = adapter.GetDocumentPosition(GetRowIndex(), nameCell.Col);

            string v = nameCell.GetText(true);
            if (DataHelper.IsEmptyValue(v)) return;
            if (DataHelper.IsRelativeInfo(v))
            {
                SetRelative(v);
            }
            else
            {
                int delim = v.IndexOf("–");
                if (delim == -1)
                {
                    throw new SmartParserException(
                        string.Format("Cannot  parse  name+occupation value {0} at row {1}", v, GetRowIndex()));
                }
                PersonName = v.Substring(0, delim);
                Occupation = v.Substring(delim + 1);
            }
        }

        public void InitPersonData()
        {
            if (this.ColumnOrdering.ContainsField(DeclarationField.RelativeTypeStrict))
            {
                SetRelative ( GetDeclarationField(DeclarationField.RelativeTypeStrict).Text.CleanWhitespace());
            }

            string nameOrRelativeType;
            if (this.ColumnOrdering.ContainsField(DeclarationField.NameAndOccupationOrRelativeType))
            {
                DivideNameAndOccupation();
            }
            else
            {
                var nameCell = GetDeclarationField(DeclarationField.NameOrRelativeType);
                nameOrRelativeType = nameCell.Text.CleanWhitespace();
                NameDocPosition = adapter.GetDocumentPosition(GetRowIndex(), nameCell.Col);
                if (this.ColumnOrdering.ContainsField(DeclarationField.Occupation))
                {
                    Occupation = GetDeclarationField(DeclarationField.Occupation).Text;
                }
                if (!DataHelper.IsEmptyValue(nameOrRelativeType))
                {
                    if (DataHelper.IsRelativeInfo(nameOrRelativeType))
                    {
                        SetRelative(nameOrRelativeType);
                    }
                    else
                    { 
                        PersonName = nameOrRelativeType;
                    }
                }
            }
        }



        public List<Cell> Cells;
        IAdapter adapter;
        public ColumnOrdering ColumnOrdering;
        int row;
        private Dictionary<DeclarationField, Cell> MappedHeader = null;
        
        //Initialized by InitPersonData
        public string PersonName = "";
        public string RelativeType = "";
        public string NameDocPosition = "";
        public string Occupation = "";

    }


}
