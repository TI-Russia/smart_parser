using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    public class ColumnDetectorException : Exception
    {
        public ColumnDetectorException(string message) : base(message)
        {
        }
    }

    public class ColumnDetector
    {
        static public bool GetValuesFromTitle(string text, ref string title, ref int? year, ref string ministry)
        {
            int text_len = text.Length;
            if (title == null)
                title = text;
            else
                title += " " + text;

            string[] title_words = { "сведения", "обязательствах", "доход", "период" };
            bool has_title_words = Array.Exists(title_words, s => text.Contains(s));
            if (!has_title_words)
                return false;

            text = Regex.Replace(text, "8\\s+июля\\s+2013", "");
            var matches = Regex.Matches(text, @"\b20\d\d\b");

            if (matches.Count > 0)
            {
                year = int.Parse(matches[0].Value);
            }
            var minMatch = Regex.Match(text, @"Министерства(.+)Российской Федерации", RegexOptions.IgnoreCase);
            if (minMatch.Success)
            {
                ministry = minMatch.Groups[1].Value;
            }

            return true;
        }

        public static bool WeakHeaderCheck(List<Cell> cells)
        {
            int colCount = 0;
            if (cells.Count < 3) return false;
            foreach (var c in cells)
            {
                if (colCount == 0 && HeaderHelpers.IsNumber(c.Text)) return true;
                if (HeaderHelpers.IsName(c.Text)) return true;
                colCount += 1;
                if (colCount > 3) break;
            }
            return false;
        }

        static int ProcessTitle(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            int row = 0;
            string title = null;
            string ministry = null;
            int? year = null;

            bool findTitle = false;
            bool prevRowIsSection = false;
            while (true)
            {
                var currRow = adapter.GetCells(row);
                string section_text;
                bool isSection = IAdapter.IsSectionRow(currRow,  adapter.GetColsCount(), prevRowIsSection, out section_text);
                if (isSection)
                {
                    if (section_text.Length > 20)
                    {
                        if (GetValuesFromTitle(section_text, ref title, ref year, ref ministry))
                        {
                            findTitle = true;
                        }
                    }
                    else
                    {
                        columnOrdering.Section = section_text;
                    }
                }
                else if (WeakHeaderCheck(currRow))
                    break;

                row += 1;

                if (row >= adapter.GetRowsCount())
                {
                    throw new ColumnDetectorException(String.Format("Headers not found"));
                }
                prevRowIsSection = isSection;
            }
            if (!findTitle) {
                if (GetValuesFromTitle(adapter.GetTitleOutsideTheTable(), ref title, ref year, ref ministry))
                {
                    findTitle = true;
                }
            }

            if (findTitle)
            {
                columnOrdering.Title = title;
                columnOrdering.Year = year;
                columnOrdering.MinistryName = ministry;
            }
            return row;
        }
        static List<Cell> FindSubcellsUnder(IAdapter adapter, Cell cell)
        {
            var subCells = new List<Cell>();
            if (cell.Row + cell.MergedRowsCount >= adapter.GetRowsCount() )
            {
                return subCells;
            }
            if (cell.CellWidth ==  0)
            {
                return subCells;
            }
            var undercCells = adapter.GetCells(cell.Row + cell.MergedRowsCount);
            foreach (var underCell in undercCells)
            {
                if (underCell.Col < cell.Col)
                    continue;
                if (underCell.Col >= cell.Col + cell.MergedColsCount)
                    break;
                if (!underCell.IsEmpty)
                    subCells.Add(underCell);
            }
            return subCells;
        }
        static void AddColumn(ColumnOrdering ordering, DeclarationField field, Cell  cell)
        {
            TColumnInfo s = new TColumnInfo();
            s.BeginColumn = cell.Col;
            s.EndColumn = cell.Col + cell.MergedColsCount;
            s.ColumnPixelWidth = cell.CellWidth;
            //s.ColumnPixelStart is unknown and initialized in FinishOrderingBuilding
            s.Field = field;

            ordering.Add(s);
        }

        static void FixMissingSubheadersForMixedRealEstate(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            //see DepEnergo2010.doc  in tests
            if (!columnOrdering.ContainsField(DeclarationField.MixedColumnWithNaturalText))
            {
                return;
            }
            TColumnInfo dummy;
            var headerCell = adapter.GetDeclarationFieldWeak(columnOrdering, columnOrdering.HeaderBegin.Value, DeclarationField.MixedColumnWithNaturalText,out dummy);
            var subCells = FindSubcellsUnder(adapter, headerCell);
            if (subCells.Count != 3)
            {
                return;
            }
            for (int row = columnOrdering.FirstDataRow; row < adapter.GetRowsCount(); row++)
            {
                if (row > columnOrdering.FirstDataRow + 5) break;
                // we check only the  second column, todo check the  first one and  the third
                string areaStr = adapter.GetCell(row, subCells[1].Col).GetText(true);
                if (!DataHelper.ParseSquare(areaStr).HasValue)
                {
                    return;
                }
            }
            AddColumn(columnOrdering, DeclarationField.MixedRealEstateType, subCells[0]);
            AddColumn(columnOrdering, DeclarationField.MixedRealEstateSquare, subCells[1]);
            AddColumn(columnOrdering, DeclarationField.MixedRealEstateCountry, subCells[2]);
            columnOrdering.Delete(DeclarationField.MixedColumnWithNaturalText);
        }

        static void FixBadColumnName01_Template(ColumnOrdering c, DeclarationField naturalText, DeclarationField country, DeclarationField square, DeclarationField type)
        {
            //move MixedColumnWithNaturalText  to MixedRealEstateType
            if (!c.ContainsField(naturalText)) return;
            if (c.ContainsField(country)
                    && c.ContainsField(square)
                )
            {
                TColumnInfo s = c.ColumnOrder[naturalText];
                s.Field = type;
                c.Add(s);
                c.Delete(naturalText);
            }
        }

        static void FixBadColumnName01(ColumnOrdering c)
        {
            FixBadColumnName01_Template(c,
                DeclarationField.MixedColumnWithNaturalText,
                DeclarationField.MixedRealEstateCountry,
                DeclarationField.MixedRealEstateSquare,
                DeclarationField.MixedRealEstateType);
            FixBadColumnName01_Template(c,
                DeclarationField.StateColumnWithNaturalText,
                DeclarationField.StatePropertyCountry,
                DeclarationField.StatePropertySquare,
                DeclarationField.StatePropertyType);
            FixBadColumnName01_Template(c,
                DeclarationField.OwnedColumnWithNaturalText,
                DeclarationField.OwnedRealEstateCountry,
                DeclarationField.OwnedRealEstateSquare,
                DeclarationField.OwnedRealEstateType);
        }

        static void FixBadColumnName02(ColumnOrdering c)
        {
            //move NameAndOccupationOrRelativeType  to NameOrRelativeType if Occupation  is present
            if (     c.ContainsField(DeclarationField.NameAndOccupationOrRelativeType)
                  && c.ContainsField(DeclarationField.Occupation)
                )
            {
                TColumnInfo s = c.ColumnOrder[DeclarationField.NameAndOccupationOrRelativeType];
                s.Field = DeclarationField.NameOrRelativeType;
                c.Add(s);
                c.Delete(DeclarationField.NameAndOccupationOrRelativeType);
            }
        }


        static public ColumnOrdering ExamineTableBeginning(IAdapter adapter)
        {
            ColumnOrdering columnOrdering = new ColumnOrdering();
            int headerStartRow = ProcessTitle(adapter, columnOrdering);
            ReadHeader(adapter, headerStartRow, columnOrdering);
            return columnOrdering;
        }

        static public List<Cell> GetColumnCells(IAdapter adapter, int headerStartRow, out int headerEndRow)
        {
            headerEndRow = headerStartRow + 1;
            var firstRow = adapter.GetCells(headerStartRow);

            List<Cell> columnCells =  new List<Cell>();
            bool headerCanHaveSecondLevel = true;
            foreach (var cell in firstRow)
            {
                string text = cell.GetText(true);
                if (cell.CellWidth == 0) continue;
                var underCells = FindSubcellsUnder(adapter, cell);

                if (underCells.Count() <= 1 || !headerCanHaveSecondLevel)
                {
                    headerEndRow = Math.Max(headerEndRow, cell.Row + cell.MergedRowsCount);
                    columnCells.Add(cell);
                    
                    // обработка ошибки документа DepEnergo2010
                    if (columnCells.Count == 1 && cell.MergedRowsCount == 1 && underCells.Count == 1)
                    {
                        string cellBelowName = underCells[0].GetText(true);
                        headerCanHaveSecondLevel = cellBelowName.Length == 0;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    foreach (var underCell in underCells)
                    {
                        underCell.TextAbove = cell.GetText(true);
                        columnCells.Add(underCell);
                    }
                    headerEndRow = Math.Max(headerEndRow, underCells[0].Row + underCells[0].MergedRowsCount);
                }
            }
            return columnCells;
        }

        static DeclarationField PredictField(IAdapter adapter, Cell headerCell)
        {
            List<string> texts = new List<string>();
            int rowIndex = headerCell.Row + headerCell.MergedRowsCount;
            const int maxRowToCollect = 10;
            for (int i = 0; i < maxRowToCollect; i++)
            {
                var c = adapter.GetCell(rowIndex, headerCell.Col);
                if (c != null)
                {
                    texts.Add(c.GetText(true));
                    rowIndex += c.MergedRowsCount;
                }
                else
                {
                    rowIndex += 1;
                }
                
                if (rowIndex >= adapter.GetRowsCount()) break;
            }
            var field = ColumnPredictor.ClassifyStrings(texts);
            if (headerCell.TextAbove != null)
            {
                string h = headerCell.TextAbove;
                // AllOwnTypes defined from 
                field &= ~DeclarationField.AllOwnTypes;
                if (HeaderHelpers.IsMixedColumn(h))
                {
                    field |= DeclarationField.Mixed;
                }
                else if (HeaderHelpers.IsStateColumn(h))
                {
                    field |= DeclarationField.State;
                }
                else if (HeaderHelpers.IsOwnedColumn(h))
                {
                    field |= DeclarationField.Owned;
                }
            }
            return field;
        }
        static public void MapStringsToConstants(IAdapter adapter, List<Cell> cells, ColumnOrdering columnOrdering)
        {
            foreach (var cell in cells)
            {
                string text = cell.GetText(true);
                Logger.Debug("column title: " + text.ReplaceEolnWithSpace().CoalesceWhitespace());
                DeclarationField field;
                if (text == "")
                {
                    field = PredictField(adapter, cell);
                    Logger.Debug("Predict: " + field.ToString());
                }
                else {
                    if (cell.TextAbove != null)
                    {
                        text = cell.TextAbove + " " + text;
                    }
                    field = HeaderHelpers.GetField(text.Replace('\n', ' '));
                }

                if (field == DeclarationField.None)
                {
                    throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} title:{1}", cell.Row, text));
                }
                AddColumn(columnOrdering, field, cell);
            }
        }

        static public void ReadHeader(IAdapter adapter, int headerStartRow, ColumnOrdering columnOrdering)
        { 
            int headerEndRow;
            var cells = GetColumnCells(adapter, headerStartRow, out headerEndRow);
            MapStringsToConstants(adapter, cells, columnOrdering);

            columnOrdering.HeaderBegin = headerStartRow;
            columnOrdering.HeaderEnd = headerEndRow;
            int firstDataRow = columnOrdering.HeaderEnd.Value;

            // пропускаем колонку с номерами
            if (firstDataRow < adapter.GetRowsCount())
            {
                string cellText1 = adapter.GetCell(firstDataRow, 0).GetText();
                string cellText2 = adapter.GetCell(firstDataRow, 1).GetText();
                if (cellText1 == "1" && cellText2 == "2")
                {
                    firstDataRow++;
                }
            }

            columnOrdering.FirstDataRow = firstDataRow;

            if (columnOrdering.ColumnOrder.Count() == 0)
            {
                throw new SmartParserException("cannot find headers");
            }
            // todo check whether we need them
            FixMissingSubheadersForMixedRealEstate(adapter, columnOrdering);
            FixBadColumnName01(columnOrdering);
            FixBadColumnName02(columnOrdering);
            columnOrdering.FinishOrderingBuilding();
        }
    }
}
