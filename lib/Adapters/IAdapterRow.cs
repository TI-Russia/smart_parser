using SmartParser.Lib;
using static SmartParser.Lib.SmartParserException;
using StringHelpers;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
    

namespace SmartParser.Lib
{
    public class DataRow : IDataRow
    {

        void MapCells()
        {
            MappedHeader = MapByOrderAndIntersection(ColumnOrdering, Cells);
            if (MappedHeader == null)
            {
                MappedHeader = MapByMaxIntersection(ColumnOrdering, Cells);
            }
        }
        public DataRow(IAdapter adapter, TableHeader columnOrdering, int row)
        {
            this.row = row;
            this.adapter = adapter;
            this.ColumnOrdering = columnOrdering;
            Cells = adapter.GetDataCells(row, columnOrdering.GetMaxColumnEndIndex());
            if (!this.adapter.IsExcel())
                MapCells();
            
        }
        public string DebugString()
        {
            string s = "";
            foreach (var c in Cells)
            {
                s += string.Format("\"{0}\"[{1}], ",c.Text.Replace("\n", "\\n"),c.CellWidth);
            }
            return s;
        }

        public DataRow DeepClone()
        {
            DataRow other =  new DataRow(this.adapter, this.ColumnOrdering, this.row);
            other.Cells = new List<Cell>();
            foreach (var x in this.Cells)
            {
                Cell c = x.ShallowCopy();
                c.IsEmpty = true;
                c.Text = "";
                other.Cells.Add(c);
            }
            other.MapCells();
            return other;
        }

        static Dictionary<DeclarationField, Cell> MapByOrderAndIntersection(TableHeader columnOrdering, List<Cell> cells)
        {
            if (columnOrdering.MergedColumnOrder.Count != cells.Count)
            {
                return null;
            }
            int start = cells[0].AdditTableIndention;
            var res = new Dictionary<DeclarationField, Cell>();
            int pixelErrorCount = 0;
            for (int i = 0; i < cells.Count; i++)
            {
                int s1 = start;
                int e1 = start + cells[i].CellWidth;
                var colInfo = columnOrdering.MergedColumnOrder[i];
                int s2 = colInfo.ColumnPixelStart;
                int e2 = colInfo.ColumnPixelStart + colInfo.ColumnPixelWidth;
                if (TableHeader.PeriodIntersection(s1, e1, s2, e2) == 0)
                {
                    pixelErrorCount += 1;
                    if (!DataHelper.IsEmptyValue(cells[i].Text)) 
                    {
                        if (!ColumnByDataPredictor.TestFieldWithoutOwntypes(colInfo.Field, cells[i]))
                        {
                            Logger.Debug(string.Format("cannot map column N={0} text={1}", i, cells[i].Text.Replace("\n", "\\n")));
                            return null;
                        }
                        else
                        {
                            Logger.Debug(string.Format("found semantic argument for mapping N={0} text={1} to {2}", 
                                i, cells[i].Text.Replace("\n", "\\n"), colInfo.Field));
                            pixelErrorCount = 0;
                        }
                    }
                }
                res[columnOrdering.MergedColumnOrder[i].Field] = cells[i];

                start = e1;
            }
            if (pixelErrorCount >= 3)
            {
                return null;
            }
            return res;

        }

        static Dictionary<DeclarationField, Cell> MapByMaxIntersection(TableHeader columnOrdering, List<Cell> cells)
        {
            Logger.Debug("MapByMaxIntersection");
            // map two header cells to one data cell
            // see dnko-2014.docx for an example

            var res = new Dictionary<DeclarationField, Cell>();
            var sizes = new Dictionary<DeclarationField, int>();
            if (cells.Count == 0) return res;
            int start = cells[0].AdditTableIndention;
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
                        //Logger.Debug(string.Format("map {1} to {0}", field, c.Text.Replace("\n", "\\n")));
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
            for (int i = 0; i < Cells.Count() && i < other.Cells.Count(); i++)
            {
                Cells[i].Text += " " + other.Cells[i].Text;
            }
        }

        public Cell GetDeclarationField(DeclarationField field, bool except = true)
        {
            try {
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
                for (int i = colSpan.BeginColumn + exactCell.MergedColsCount; i < colSpan.EndColumn;)
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
            catch (SmartParserFieldNotFoundException e)
            {
                if (!except)
                    return null;
                throw e;
            }

        }

        public string GetContents(DeclarationField field, bool except = true)
        {
            if (!ColumnOrdering.ContainsField(field))
            {
                if (!except)
                    return "";
            }

            Cell c;
            try
            {
                c = GetDeclarationField(field);
            }
            catch (SmartParserFieldNotFoundException e)
            {
                if (!except)
                    return "";
                
                throw new SmartParserFieldNotFoundException(e.Message + String.Format(" Line = {0}", this.DebugString())); 
            }

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
            if (this.ColumnOrdering.ContainsField(DeclarationField.DeclarantIndex))
            {
                string indexStr = GetDeclarationField(DeclarationField.DeclarantIndex).Text
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

        public void SetRelative(string value)
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
        bool DivideNameAndOccupation(Cell nameCell)
        {
            NameDocPosition = adapter.GetDocumentPosition(GetRowIndex(), nameCell.Col);

            string v = nameCell.GetText(true);
            if (DataHelper.IsEmptyValue(v)) return true;
            if (DataHelper.IsRelativeInfo(v))
            {
                SetRelative(v);
            }
            else
            {
                string pattern = @"\s+\p{Pd}\s+"; // UnicodeCategory.DashPunctuation
                v = Regex.Replace(v, @"\d+\.\s+", "");
                string[] two_parts = Regex.Split(v, pattern);
                string clean_v = Regex.Replace(v, pattern, " ");
                string[] words = Regex.Split(clean_v, @"[\,\s\n]+");
                
                if (words.Length >= 3 && TextHelpers.CanBePatronymic(words[2]) 
                                      && !TextHelpers.MayContainsRole(words[0])
                                      && !TextHelpers.MayContainsRole(words[1]))
                {
                    // ex: "Рутенберг Дмитрий Анатольевич начальник управления"
                    PersonName = String.Join(" ", words.Take(3)).Trim();
                    Occupation = String.Join(" ", words.Skip(3)).Trim();
                }
                else if (TextHelpers.CanBePatronymic(words.Last()))
                {
                    // ex: "начальник управления Рутенберг Дмитрий Анатольевич"
                    PersonName = String.Join(" ", words.Skip(words.Length - 3)).Trim();
                    Occupation = String.Join(" ", words.Take(words.Length - 3)).Trim();
                }
                else if (Regex.Match(v, @"\w\.\w\.,").Success)
                {
                    // ex: "Головачева Н.В., заместитель"
                    var match = Regex.Match(v, @"\w\.\w\.,");
                    PersonName = v.Substring(0, match.Index + match.Length - 1).Trim();
                    Occupation = v.Substring(match.Index + match.Length).Trim();
                }
                else if (words.Length >= 2 && TextHelpers.CanBeInitials(words[1]) && 
                            TextHelpers.MayContainsRole(String.Join(" ", words.Skip(2)).Trim()))
                {
                    // ex: "Головачева Н.В., заместитель"
                    PersonName = String.Join(" ", words.Take(2)).Trim();
                    Occupation = String.Join(" ", words.Skip(2)).Trim();
                }
                else if (two_parts.Length == 2)
                {
                    PersonName = two_parts[0].Trim();
                    Occupation = String.Join(" - ", two_parts.Skip(1)).Trim();
                }
                else
                {
                    // maybe PDF has split cells (table on different pages)
                    // example file: "5966/14 Upravlenie delami.pdf" converted to docx
                    Logger.Error(string.Format("Cannot parse name+occupation value {0} at row {1}", v, GetRowIndex()));
                    return false;
                }
            }
            return true;
        }

        bool DivideIndexAndName(Cell nameCell)
        {
            NameDocPosition = adapter.GetDocumentPosition(GetRowIndex(), nameCell.Col);

            string v = nameCell.GetText(true);
            if (DataHelper.IsEmptyValue(v)) return true;
            if (DataHelper.IsRelativeInfo(v))
            {
                SetRelative(v);
            }
            else
            {
                string pattern = @"\s*\d+[\.\)]\s*(\w.+)";
                var match = Regex.Match(v, pattern);
                if (match == null || !match.Success)
                {
                    Logger.Debug(String.Format("cannot parser index and name: {0}", v));
                    return false;
                }
                PersonName = match.Groups[1].Value.Trim();

            }
            return true;
        }

        public static bool CheckPersonName(String s)
        {
            if (s.Contains('.')) {
                return true;
            }

            bool hasSpaces = s.Trim().Any(Char.IsWhiteSpace);
            if (!hasSpaces)
            {
                return false;
            }
            string[] words = Regex.Split(s, @"[\,\s\n]+");
            if (TextHelpers.CanBePatronymic(words[words.Length - 1])) {
                return true;
            }
            if (words.Count() != 3) {
                var predictedField = ColumnByDataPredictor.PredictByString(s);
                if (!HeaderHelpers.IsNameDeclarationField(predictedField)) 
                {
                    return false;
                }
            }
            return true;
        }
        public bool InitPersonData(string prevPersonName)
        {
            if (this.ColumnOrdering.ContainsField(DeclarationField.RelativeTypeStrict))
            {
                SetRelative ( GetDeclarationField(DeclarationField.RelativeTypeStrict).Text.ReplaceEolnWithSpace());
            }

            string nameOrRelativeType;
            if (this.ColumnOrdering.ContainsField(DeclarationField.NameAndOccupationOrRelativeType))
            {
                if (!TableHeader.SearchForFioColumnOnly)
                {
                    if (!DivideNameAndOccupation(GetDeclarationField(DeclarationField.NameAndOccupationOrRelativeType)))
                    {
                        return false;
                    }
                }
            }
            else if (this.ColumnOrdering.ContainsField(DeclarationField.DeclarantIndexAndName))
            {
                if (!DivideIndexAndName(GetDeclarationField(DeclarationField.DeclarantIndexAndName)))
                {
                    return false;
                }
            }
            else
            {
                var nameCell = GetDeclarationField(DeclarationField.NameOrRelativeType);
                nameOrRelativeType = nameCell.Text.ReplaceEolnWithSpace().Replace("не имеет", "");
                NameDocPosition = adapter.GetDocumentPosition(GetRowIndex(), nameCell.Col);
                if (this.ColumnOrdering.ContainsField(DeclarationField.Occupation))
                {
                    Occupation = GetDeclarationField(DeclarationField.Occupation).Text;
                }
                if (this.ColumnOrdering.ContainsField(DeclarationField.Department))
                {
                    Department = GetDeclarationField(DeclarationField.Department).Text;
                }
                else if (adapter.GetDocumentDepartmentFromMetaTag() != null)
                {
                    Department = adapter.GetDocumentDepartmentFromMetaTag();
                }

                if (!DataHelper.IsEmptyValue(nameOrRelativeType))
                {
                    if (DataHelper.IsRelativeInfo(nameOrRelativeType))
                    {
                        SetRelative(nameOrRelativeType);
                    }
                    else if (prevPersonName == nameOrRelativeType && DataHelper.IsRelativeInfo(Occupation))
                    {
                        SetRelative(Occupation);
                    }
                    else if (nameOrRelativeType.Trim(',').Contains(",") ||
                                (nameOrRelativeType.Contains(" -")
                                && Regex.Split(nameOrRelativeType, @"[\,\s\n]+").Count() > 3))
                    {
                        if (!DivideNameAndOccupation(nameCell))
                        {
                            return false;
                        }
                    }
                    else
                    {
                        PersonName = nameOrRelativeType;
                        if (!CheckPersonName(PersonName))
                        {
                            Logger.Error("ignore bad person name " + PersonName);
                            return false;
                        }
                    }
                }
            }
            if (ColumnOrdering.ContainsField(DeclarationField.OccupationOrRelativeType))
            {
                var str = GetDeclarationField(DeclarationField.OccupationOrRelativeType).GetText();
                var relType = DataHelper.ParseRelationType(str, false);
                if (relType == RelationType.Error)
                {
                    Occupation = str;
                }
                else
                {
                    RelativeType = str;
                }
            }
            return true;
        }



        public List<Cell> Cells;
        public IAdapter adapter;
        public TableHeader ColumnOrdering;
        int row;
        private Dictionary<DeclarationField, Cell> MappedHeader = null;
        
        //Initialized by InitPersonData
        public string PersonName = "";
        public string RelativeType = "";
        public string NameDocPosition = "";
        public string Occupation = "";
        public string Department = null;
    }


}
