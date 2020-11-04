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
using System.Drawing;
using System.Drawing.Text;


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

        public Cell ShallowCopy()
        {
            return (Cell)this.MemberwiseClone();
        }

        public virtual string GetText(bool trim = true)
        {
            var text = Text;
            if (trim)
            {
                text = text.CoalesceWhitespace().Trim();
            }

            return text;
        }

        public override string ToString()
        {
            return Text;
        }

        public List<string> GetLinesWithSoftBreaks()
        {
            var res = new List<string>();
            if (IsEmpty) return res;
            string[] hardLines = Text.Split('\n');
            var graphics = System.Drawing.Graphics.FromImage(new Bitmap(1, 1));
            graphics.TextRenderingHint = TextRenderingHint.SingleBitPerPixelGridFit;
            graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.None;
            graphics.CompositingQuality = System.Drawing.Drawing2D.CompositingQuality.HighSpeed;
            graphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Low;
            
            var stringSize = new SizeF();
            var font = new System.Drawing.Font(FontName, FontSize / 2);
            foreach (var hardLine in hardLines)
            {
                stringSize = graphics.MeasureString(hardLine, font);
                // Logger.Info("stringSize = {0} (FontName = {2}, fontsize = {1})", stringSize, FontSize / 2, FontName);

                int defaultMargin = 11; //to do calc it really
                int softLinesCount = (int)(stringSize.Width / (CellWidth - defaultMargin)) + 1;
                if (softLinesCount == 1)
                {
                    res.Add(hardLine);
                }
                else
                {
                    int start = 0;
                    for (int k = 0; k < softLinesCount; ++k)
                    {
                        int len;
                        if (k + 1 == softLinesCount)
                        {
                            len = hardLine.Length - start;
                        }
                        else
                        {
                            len = (int)(hardLine.Length / softLinesCount);
                            int wordBreak = (start + len >= hardLine.Length) ? hardLine.Length : hardLine.LastIndexOf(' ', start + len);
                            if (wordBreak > start)
                            {
                                len = wordBreak - start;
                            }
                            else
                            {
                                wordBreak = hardLine.IndexOf(' ', start + 1);
                                len = (wordBreak == -1) ? hardLine.Length - start : wordBreak - start;
                            }
                        }
                        res.Add(hardLine.Substring(start, len));
                        start += len;
                        if (start >= hardLine.Length) break;
                    }
                }
            }
            // Logger.Info("result = {0}", string.Join("|\n", res));
            return res;
        }


        public int Row { get; set; } = -1;
        public int Col { get; set; } = -1; // not merged column index

        public int CellWidth = 0; // in pixels
        public int AdditTableIndention = 0; // only for Word: http://officeopenxml.com/WPtableIndent.php
        public string FontName;
        public int FontSize;

    };

    public class DataRow : DataRowInterface
    {

        void MapCells()
        {
            MappedHeader = MapByOrderAndIntersection(ColumnOrdering, Cells);
            if (MappedHeader == null)
            {
                MappedHeader = MapByMaxIntersection(ColumnOrdering, Cells);
            }
        }
        public DataRow(IAdapter adapter, ColumnOrdering columnOrdering, int row)
        {
            this.row = row;
            this.adapter = adapter;
            this.ColumnOrdering = columnOrdering;
            Cells = adapter.GetCells(row, columnOrdering.GetMaxColumnEndIndex());
            if (!this.adapter.IsExcel())
                MapCells();
            
        }
        public string DebugString()
        {
            var s = new StringBuilder();
            foreach (var c in Cells)
            {
                s.AppendFormat("\"{0}\"[{1}], ", c.Text, c.CellWidth);
            }
            s.Replace("\n", "\\n");

            return s.ToString();
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

        static Dictionary<DeclarationField, Cell> MapByOrderAndIntersection(ColumnOrdering columnOrdering, List<Cell> cells)
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
                if (ColumnOrdering.PeriodIntersection(s1, e1, s2, e2) == 0)
                {
                    pixelErrorCount += 1;
                    if (!DataHelper.IsEmptyValue(cells[i].Text)) 
                    {
                        if (!ColumnPredictor.TestFieldWithoutOwntypes(colInfo.Field, cells[i]))
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

        static Dictionary<DeclarationField, Cell> MapByMaxIntersection(ColumnOrdering columnOrdering, List<Cell> cells)
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
                    if (field == DeclarationField.None && !string.IsNullOrWhiteSpace(c.Text))
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

        public Cell GetDeclarationField(DeclarationField field)
        {
            Cell cell;
            if (MappedHeader != null && MappedHeader.TryGetValue(field, out cell))
            {
                return cell;
            }
            TColumnInfo colSpan;
            var exactCell = adapter.GetDeclarationFieldWeak(ColumnOrdering, row, field, out colSpan);
            if (!string.IsNullOrWhiteSpace(exactCell.Text) || exactCell.Col == -1)
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
                if (!string.IsNullOrWhiteSpace(mergedCell.Text))
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

            Cell c;
            try
            {
                c = GetDeclarationField(field);
            }
            catch (SmartParserFieldNotFoundException e)
            {
                if (!except)
                    return "";
                throw e; 
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
                else if (words.Length >= 2 && TextHelpers.CanBeInitials(words[1]) && TextHelpers.MayContainsRole(String.Join(" ", words.Skip(2)).Trim()))
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
                    throw new SmartParserException(
                        string.Format("Cannot parse name+occupation value {0} at row {1}", v, GetRowIndex()));
                }
            }
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
                if (!ColumnOrdering.SearchForFioColumnOnly)
                {
                    try
                    {
                        DivideNameAndOccupation();    
                    }
                    catch (SmartParserException) {
                        // maybe PDF has split cells (table on different pages)
                        // example file: "5966/14 Upravlenie delami.pdf" converted to docx
                        var nameCell = GetDeclarationField(DeclarationField.NameAndOccupationOrRelativeType);
                        Logger.Error("ignore bad person name " + nameCell);
                        return false;
                    }
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
                    else
                    { 
                        PersonName = nameOrRelativeType;
                        if (!PersonName.Contains('.') && !PersonName.Trim().Any(Char.IsWhiteSpace)) {
                            Logger.Error("ignore bad person name " + PersonName);
                            return false;
                        }
                    }
                }
            }
            return true;
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
        public string Department = null;
    }


}
