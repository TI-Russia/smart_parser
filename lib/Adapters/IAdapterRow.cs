using Parser.Lib;
using static Parser.Lib.SmartParserException;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Smart.Parser.Lib;
using TI.Declarator.ParserCommon;
using System.Text.RegularExpressions;


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

        public string TextAbove = null;

        public virtual string GetText(bool trim = true)
        {
            var text = Text;
            if (trim)
            {
                text = text.CoalesceWhitespace().Trim();
            }

            return text;
        }

        public int Row { get; set; } = -1;
        public int Col { get; set; } = -1;

        public int CellWidth = 0;
    };

    public class DataRow : DataRowInterface
    {

        public DataRow(IAdapter adapter, ColumnOrdering columnOrdering, int row)
        {
            this.row = row;
            this.adapter = adapter;
            this.ColumnOrdering = columnOrdering;
            Cells = adapter.GetCells(row, columnOrdering.GetMaxColumnEndIndex());
            MappedHeader = MapByOrderAndIntersection(columnOrdering, Cells);
            if (MappedHeader == null )
            {
                MappedHeader = MapByMaxIntersection(columnOrdering, Cells);
            }
            
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
                    if (!ColumnPredictor.TestFieldWithoutOwntypes(colInfo.Field, cells[i]))
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
            var sizes = new Dictionary<DeclarationField, int>();
            int start = 0;
            foreach (var c in cells)
            {
                if (c.CellWidth >  0 )
                {
                    int interSize = 0;
                    var field = columnOrdering.FindByPixelIntersection(start, start + c.CellWidth, out interSize);
                   
                    // cannot map some text,so it is a failure
                    if (field == DeclarationField.None && c.Text.Trim().Length > 0)
                    {
                        return null;
                    }
                    // take only fields with maximal pixel intersection
                    if (!sizes.ContainsKey(field) || sizes[field] < interSize)
                    {
                        res[field] = c;
                        sizes[field] = interSize;
                    }
                }
                start += c.CellWidth;
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
            TColumnInfo colSpan;
            var exactCell = adapter.GetDeclarationFieldWeak(ColumnOrdering, row, field, out colSpan);
            if (exactCell.Text.Trim() != "")
            {
                return exactCell;
            }
            for (int i = exactCell.Col + exactCell.MergedColsCount; i < colSpan.EndColumn;)
            {
                var mergedCell = adapter.GetCell(row, i);
                if (mergedCell == null)
                {
                    break;
                }
                if (mergedCell.Text.Trim() != "")
                {
                    return mergedCell;
                }
                i += mergedCell.MergedColsCount;
            }
            return exactCell;

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
                    .Replace(".", "").ReplaceEolnWithSpace();
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
            if (DataHelper.IsEmptyValue(value))
            {
                value = String.Empty;
            }
            RelativeType = value;
            if (RelativeType != String.Empty && !DataHelper.IsRelativeInfo(RelativeType))
            {
                throw new SmartParserException(
                    string.Format("Wrong relative type {0} at row {1}", RelativeType, GetRowIndex()));
            }
        }
        static bool CanBePatronymic(string s)
        {
            if (s.Length == 0) return false;
            if (!Char.IsUpper(s[0])) return false;
            return s.EndsWith("вич") || 
                    s.EndsWith("вна") ||
                    s.EndsWith("вны") ||
                    s.EndsWith(".") ||
                    s.EndsWith("тич") ||
                    s.EndsWith("мич") ||
                    s.EndsWith("ьич") ||
                    s.EndsWith("чна");
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
                string pattern = @"\p{Pd}"; //UnicodeCategory.DashPunctuation
                string[] result = Regex.Split(v, pattern);
                if (result.Length < 2)
                {
                    string[] words = Regex.Split(v, @"\s+");
                    if (words.Length >= 3 && CanBePatronymic(words[2]))
                    {
                        PersonName = String.Join(" ", words.Take(3)).Trim();
                        Occupation = String.Join(" ", words.Skip(3)).Trim();

                    }
                    else
                    {
                        throw new SmartParserException(
                            string.Format("Cannot  parse  name+occupation value {0} at row {1}", v, GetRowIndex()));
                    }
                }
                else
                {
                    PersonName = result[0].Trim();
                    Occupation = String.Join("-", result.Skip(1)).Trim();
                }
            }
        }

        public void InitPersonData()
        {
            if (this.ColumnOrdering.ContainsField(DeclarationField.RelativeTypeStrict))
            {
                SetRelative ( GetDeclarationField(DeclarationField.RelativeTypeStrict).Text.ReplaceEolnWithSpace());
            }

            string nameOrRelativeType;
            if (this.ColumnOrdering.ContainsField(DeclarationField.NameAndOccupationOrRelativeType))
            {
                DivideNameAndOccupation();
            }
            else
            {
                var nameCell = GetDeclarationField(DeclarationField.NameOrRelativeType);
                nameOrRelativeType = nameCell.Text.ReplaceEolnWithSpace();
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
