using SmartParser.Lib;
using StringHelpers;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace SmartParser.Lib
{
    public class ColumnDetectorException : Exception
    {
        public ColumnDetectorException(string message) : base(message)
        {
        }
    }

    public class ColumnDetector
    {
        public static List<string> AbsenceMarkers = new List<string> { "-", "отсутствует", "?", "не указано", "не имеет"};
        
        public static string CheckDate(Match match)
        {
            // delete all dates except the first ones or the last ones 01.01.2010 and 31.12.2010
            bool first_date = match.Value.StartsWith("1.1") || match.Value.StartsWith("01.01");
            bool last_date = match.Value.StartsWith("31.12");
            if (first_date || last_date)
            {
                return match.Value;
            } 
            else
            {
                return "";
            }
        }
        static public bool GetValuesFromTitle(string text, ref string title, ref int? year, ref string ministry)
        {
            int text_len = text.Length;
            if (title == null)
                title = text;
            else
                title += " " + text;
            
            text = text.ToLower();
            string[] title_words = { "сведения", "обязательствах", "доход", "период" };
            bool has_title_words = Array.Exists(title_words, s => text.Contains(s));
            if (!has_title_words)
                return false;

            text = Regex.Replace(text, "8\\s+июля\\s+2013", "");
            text = Regex.Replace(text, @"\d\d?\.\d\d?\.20\d\d", new MatchEvaluator(CheckDate));

            var decemberYearMatches = Regex.Matches(text, @"(31\s+декабря\s+)(20 *\d\d)\s+((года)|(г\.))");
            if (decemberYearMatches.Count > 0)
            {
                var year_str = decemberYearMatches[0].Groups[2].Value.RemoveCharacters(' ');
                year = int.Parse(year_str);
            }
            else
            {
                var commonYearMatches = Regex.Matches(text, @"\b20\d\d\b");
                if (commonYearMatches.Count > 0)
                {
                    year = int.Parse(commonYearMatches[0].Value);
                }
                else
                {
                    commonYearMatches = Regex.Matches(text, @"\b(20\d\d)г.");
                    if (commonYearMatches.Count > 0)
                    {
                        year = int.Parse(commonYearMatches[0].Groups[1].Value);
                    }
                }
            }
            
            var specificYearMatches = Regex.Matches(text, @"за(20\d\d)\b");
            if (specificYearMatches.Count > 0)
            {
                year = int.Parse(specificYearMatches[0].Groups[1].Value);
            }

            var minMatch = Regex.Match(text, @"Министерства(.+)Российской Федерации", RegexOptions.IgnoreCase);
            if (minMatch.Success)
            {
                ministry = minMatch.Groups[1].Value;
            }

            return true;
        }

        public static bool WeakHeaderCheck(IAdapter adapter, List<Cell> cells)
        {
            int colCount = 0;
            if (cells.Count < 3) return false;
            foreach (var c in cells)
            {
                if (colCount == 0 && HeaderHelpers.IsNumber(c.Text)) return true;
                if (HeaderHelpers.IsName(c.Text)) return true;
                if (HeaderHelpers.HasOwnedString(c.Text) || HeaderHelpers.HasStateString(c.Text))
                {
                    if (FindSubcellsUnder(adapter, c).Count >= 3)
                    {
                        return true;
                    }
                }
                colCount += 1;
                if (colCount > 3) break;
            }
            return false;
        }

        // special abridged format for Moscow courts, see sud_2016.doc in the test cases 
        public static bool IsNamePositionAndIncomeTable(List<Cell> cells)
        {
            if (cells.Count != 3) return false;

            return HeaderHelpers.IsName(cells[0].Text)
                 && HeaderHelpers.IsOccupation(cells[1].Text)
                 && HeaderHelpers.IsDeclaredYearlyIncome(cells[2].Text);
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
                bool isSection = adapter.IsSectionRow(row, currRow,  adapter.GetColsCount(), prevRowIsSection, out section_text);
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
                else if (WeakHeaderCheck(adapter, currRow))
                    break;

                row += 1;

                if (row >= adapter.GetRowsCount())
                {
                    row = 0;
                    break;
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
            if (cell.CellWidth ==  0 && cell.GetText(true).Trim() == "")
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
        static bool IsIncomeColumn(DeclarationField d)
        {
            return d == DeclarationField.DeclaredYearlyIncome ||
                d == DeclarationField.DeclaredYearlyIncomeThousands ||
                d == DeclarationField.DeclaredYearlyOtherIncome;
        }

        static void AddColumn(ColumnOrdering ordering, DeclarationField field, Cell  cell)
        {
            TColumnInfo s = new TColumnInfo();
            s.BeginColumn = cell.Col;
            s.EndColumn = cell.Col + cell.MergedColsCount;
            s.ColumnPixelWidth = cell.CellWidth;
            //s.ColumnPixelStart is unknown and initialized in FinishOrderingBuilding
            s.Field = field;
            if (IsIncomeColumn(field))
            {
                string dummy = "";
                int? year = null;
                if (ColumnDetector.GetValuesFromTitle(cell.GetText(), ref dummy, ref year, ref dummy) && year.HasValue)
                {
                    ordering.YearFromIncome = year.Value;
                }
            }

            ordering.Add(s);
        }

        static void FixMissingSubheadersForVehicle(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            if (!columnOrdering.ContainsField(DeclarationField.Vehicle))
                return;

            TColumnInfo dummy;
            var headerCell = adapter.GetDeclarationFieldWeak(columnOrdering, columnOrdering.HeaderBegin.Value, DeclarationField.Vehicle,out dummy);
            if (headerCell.MergedColsCount != 2)
                return;

            var subCells = FindSubcellsUnder(adapter, headerCell);
            if (subCells.Count == 1)
                return;

            string cleanHeader = headerCell.Text.ToLower().Replace(" ", "");
            if (cleanHeader.Contains("транспортныесредства") && cleanHeader.Contains("марка") && cleanHeader.Contains("вид"))
            {

                TColumnInfo columnVehicleType = new TColumnInfo();
                columnVehicleType.BeginColumn = headerCell.Col;
                columnVehicleType.EndColumn = headerCell.Col + 1;
                columnVehicleType.ColumnPixelWidth = headerCell.CellWidth / 2;
                columnVehicleType.Field = DeclarationField.VehicleType;
                columnOrdering.Add(columnVehicleType);

                TColumnInfo columnVehicleModel = new TColumnInfo();
                columnVehicleModel.BeginColumn = headerCell.Col + 1;
                columnVehicleModel.EndColumn = headerCell.Col + 2;
                columnVehicleModel.ColumnPixelWidth = headerCell.CellWidth / 2;
                columnVehicleModel.Field = DeclarationField.VehicleModel;
                columnOrdering.Add(columnVehicleModel);

                columnOrdering.Delete(DeclarationField.Vehicle);

            }
        }

        static bool CheckSquareColumn(IAdapter adapter, int rowStart, int rowCount, List<Cell> subCells, int subColumnNo)
        {
            for (int row = rowStart; row < adapter.GetRowsCount(); row++)
            {
                if (row > rowStart + rowCount) break;
                // we check only the  second column, todo check the  first one and  the third
                var cell = adapter.GetCell(row, subCells[subColumnNo].Col);
                if (cell == null)
                {
                    return false;   
                }
                string areaStr = cell.GetText(true);
                if (!DataHelper.IsEmptyValue(areaStr))
                {
                    if (!DataHelper.ParseSquare(areaStr).HasValue)
                    {
                        return false;
                    }
                }
            }

            return true;
        }

        static void FixMissingSubheadersForMergedColumns(IAdapter adapter, ColumnOrdering columnOrdering,
            DeclarationField mergedField, DeclarationField[] subColumns)
        {
            if (!columnOrdering.ContainsField(mergedField))
            {
                return;
            }
            TColumnInfo dummy;
            var headerCell = adapter.GetDeclarationFieldWeak(columnOrdering, columnOrdering.HeaderBegin.Value, mergedField, out dummy);
            var subCells = FindSubcellsUnder(adapter, headerCell);
            // we check only the  second column, todo check the  first one and  the third
            if (subCells.Count != subColumns.Count() || !CheckSquareColumn(adapter, columnOrdering.FirstDataRow, 5, subCells, 1))
            {
                return;
            }
            for (int i = 0; i < subColumns.Count(); ++i)
            {
                AddColumn(columnOrdering, subColumns[i], subCells[i]);
            }
            columnOrdering.Delete(mergedField);
        }

        static void FixMissingSubheadersForMixedRealEstate(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            //see DepEnergo2010.doc  in tests
            FixMissingSubheadersForMergedColumns(
                adapter,
                columnOrdering, 
                DeclarationField.MixedColumnWithNaturalText,
                new DeclarationField[] {   
                    DeclarationField.MixedRealEstateType, 
                    DeclarationField.MixedRealEstateSquare, 
                    DeclarationField.MixedRealEstateCountry}
            );
        }

        static void FixMissingSubheadersForOwnedColumn(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            //see niz_kam.docx   in tests
            FixMissingSubheadersForMergedColumns(
                adapter,
                columnOrdering,
                DeclarationField.OwnedColumnWithNaturalText,
                new DeclarationField[] {   
                    DeclarationField.OwnedRealEstateType,
                    DeclarationField.OwnedRealEstateSquare,
                    DeclarationField.OwnedRealEstateCountry,
                    DeclarationField.Vehicle
                    }
            );
        }

        static void FixMissingSubheadersForStateColumn(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            //see niz_kam.docx   in tests
            FixMissingSubheadersForMergedColumns(
                adapter,
                columnOrdering,
                DeclarationField.StateColumnWithNaturalText,
                new DeclarationField[] {
                    DeclarationField.StatePropertyType,
                    DeclarationField.StatePropertySquare,
                    DeclarationField.StatePropertyCountry,
                    }
            );

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
            int maxMergedRows = 1;
            var texts = new List<string>();
            foreach (var cell in firstRow)
            {
                string text = cell.GetText(true);

                if (adapter.GetRowsCount() == cell.MergedRowsCount)
                    continue;
                if (cell.CellWidth == 0 && text.Trim() == "") continue;

                if (maxMergedRows < cell.MergedRowsCount)
                    maxMergedRows = cell.MergedRowsCount;
                var underCells = FindSubcellsUnder(adapter, cell);

                if (underCells.Count() <= 1 || !headerCanHaveSecondLevel)
                {
                    for (int i = 0; i < cell.MergedRowsCount; ++i)
                    {
                        if (i == adapter.GetRowsCount() || !adapter.RowHasPersonName(cell.Row + i + 1))
                        {
                            headerEndRow = Math.Max(headerEndRow, cell.Row + i + 1);
                        }
                        else
                        {
                            break;
                        }
                    }
                    

                    // иногда в двухярусном заголовке в верхней клетке пусто, а в нижней есть заголовок (TwoRowHeaderEmptyTopCellTest)
                    if (text.Trim() == "" && cell.MergedRowsCount < maxMergedRows && underCells.Count() == 1) 
                    {
                        columnCells.Add(underCells.First());
                    }
                    else
                    {
                        columnCells.Add(cell);
                    }
                    
                    texts.Add(cell.Text.NormSpaces());
                    
                    // обработка ошибки документа DepEnergo2010
                    if (columnCells.Count == 1 && cell.MergedRowsCount == 1 && underCells.Count == 1)
                    {
                        string cellBelowName = underCells[0].GetText(true);
                        headerCanHaveSecondLevel = cellBelowName.Length < 5;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    foreach (var underCell in underCells)
                    {
                        var underCells2 = FindSubcellsUnder(adapter, underCell);
                        //if ((underCells2.Count() <= 1) || (maxMergedRows != 3))
                        if ((underCells2.Count() <= 1) || (underCells2.Count() > 0 && underCells2[0].Row + underCells2[0].MergedRowsCount > headerEndRow))
                        {
                            underCell.TextAbove = cell.Text.NormSpaces();
                            columnCells.Add(underCell);
                            texts.Add(underCell.TextAbove + "^" + underCell.Text.NormSpaces());
                        }
                        else
                        {
                            // three merged rows in the header, see pudoz_01.docx
                            foreach (var underCell2 in underCells2)
                            {
                                underCell2.TextAbove = cell.Text.NormSpaces() + " " + underCell.Text.NormSpaces();
                                columnCells.Add(underCell2);
                                texts.Add(underCell2.TextAbove + "^" + underCell2.Text.NormSpaces());
                            }
                        }

                    }
                    headerEndRow = Math.Max(headerEndRow, underCells[0].Row + underCells[0].MergedRowsCount);
                }
                
            }
            Logger.Debug("column titles: " + String.Join("|", texts));
            return columnCells;
        }

        
        static public void MapColumnTitlesToInnerConstants(IAdapter adapter, List<Cell> cells, ColumnOrdering columnOrdering)
        {
            foreach (var cell in cells)
            {
                string text = cell.GetText(true);
                Logger.Debug(string.Format("column title: \"{0}\"[{1}]",text.ReplaceEolnWithSpace().CoalesceWhitespace(), cell.CellWidth));
                DeclarationField field;
                string clean_text = AbsenceMarkers.Aggregate(text, (x, y) => x.Replace(y, "")).Trim();
                
                if (adapter.GetRowsCount() == cell.MergedRowsCount)
                    continue;
                
                if ((text == "" || clean_text.Length <= 1) && (text != "№"))
                {
                    // too short title, try to predict by values
                    field = ColumnPredictor.PredictEmptyColumnTitle(adapter, cell);
                    Logger.Debug("Predict: " + field.ToString());
                }
                else {
                    field = HeaderHelpers.TryGetField(cell.TextAbove, text);
                    if ((field == DeclarationField.None) && clean_text.Length <= 4)
                    {
                        field = ColumnPredictor.PredictEmptyColumnTitle(adapter, cell);
                        Logger.Debug("Predict: " + field.ToString());
                    }
                    if (field == DeclarationField.None) {
                        throw new SmartParserException(String.Format("Cannot recognize field \"{0}\"", text.Replace('\n', ' ')));
                    }

                }

                if (field == DeclarationField.None && !DataHelper.IsEmptyValue(text) )
                {
                    throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} title:{1}", cell.Row, text));
                }
                if (ColumnPredictor.CalcPrecision)
                {
                    ColumnPredictor.PredictForPrecisionCheck(adapter, cell, field);
                }
                
                AddColumn(columnOrdering, field, cell);
                if (ColumnOrdering.SearchForFioColumnOnly)
                    if  (HeaderHelpers.IsNameDeclarationField(field))
                    {
                        break;
                    }
            }
        }

        static public void ReadHeader(IAdapter adapter, int headerStartRow, ColumnOrdering columnOrdering)
        { 
            int headerEndRow;
            var cells = GetColumnCells(adapter, headerStartRow, out headerEndRow);
            MapColumnTitlesToInnerConstants(adapter, cells, columnOrdering);

            columnOrdering.HeaderBegin = headerStartRow;
            columnOrdering.HeaderEnd = headerEndRow;
            int firstDataRow = columnOrdering.HeaderEnd.Value;

            // пропускаем колонку с номерами
            if (firstDataRow < adapter.GetRowsCount())
            {
                string cellText1 = adapter.GetCell(firstDataRow, 0).GetText();
                string cellText2 = adapter.GetCell(firstDataRow, 1).GetText();
                if (cellText1.StartsWith("1") && cellText2.StartsWith("2"))
                {
                    firstDataRow++;
                }
            }

            columnOrdering.FirstDataRow = firstDataRow;

            if (columnOrdering.ColumnOrder.Count() == 0)
            {
                throw new SmartParserException("cannot find headers");
            }
            FixMissingSubheadersForMixedRealEstate(adapter, columnOrdering);
            FixMissingSubheadersForVehicle(adapter, columnOrdering);
            FixBadColumnName01(columnOrdering);
            FixBadColumnName02(columnOrdering);
            FixMissingSubheadersForOwnedColumn(adapter, columnOrdering);
            FixMissingSubheadersForStateColumn(adapter, columnOrdering);
            columnOrdering.FinishOrderingBuilding(cells[0].AdditTableIndention);
        }
    }
}
