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

        static private bool IsHeader(List<Cell> cells)
        {
            string text = "";
            int nonEmptyCellCount = 0;
            foreach (var cell in cells)
            {
                string cellText = cell.GetText(true);
                if (!String.IsNullOrWhiteSpace(cellText))
                {
                    nonEmptyCellCount++;
                }

                text += cell.GetText();
            }

            if (text.Trim() == "")
            {
                return false;
            }

            string first = cells.First().GetText(true);

            return (nonEmptyCellCount > 4) &&
                   (cells.First().GetText(true) != "1");
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
                bool isSection = adapter.IsSectionRow(currRow, prevRowIsSection, out section_text);
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
                else if (IsHeader(currRow))
                    break;

                row += 1;

                if (row >= adapter.GetRowsCount())
                {
                    throw new ColumnDetectorException(String.Format("Headers not found"));
                }
                prevRowIsSection = isSection;
            }
            if (!findTitle) {
                if (GetValuesFromTitle(adapter.GetTitle(), ref title, ref year, ref ministry))
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
            var undercCells = adapter.GetCells(cell.Row + cell.MergedRowsCount);
            var subCells = new List<Cell>();
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
        static void SecondLevelHeader(IAdapter adapter, Cell parentCell, List<Cell> subCells, ColumnOrdering result)
        {
            string text = parentCell.GetText(true);
            DeclarationField prev_field = DeclarationField.None;

            foreach (var cell in subCells)
            {
                string cellText = cell.GetText(true);
                string fullText = text + " " + cellText;

                DeclarationField field = DeclarationField.None;
                if (cellText == "" && prev_field == DeclarationField.StatePropertySquare)
                {
                    //  пустая колонка страны (предыдущая колонка - площадь)
                    field = DeclarationField.StatePropertyCountry;
                }
                else if (cellText == "" && prev_field == DeclarationField.None) {
                    // пустая колонка, перед которой ничего не было (скорее всего "вид недвижимости")
                    // пример такого файла: 9037\rabotniki_podved_organizacii_2013.xlsx
                    field = DeclarationField.OwnedRealEstateType;
                }
                else
                {
                    field = HeaderHelpers.TryGetField(fullText);
                }


                if (field == DeclarationField.None)
                {
                    throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1} text:'{2}'", cell.Row, cell.Col, fullText));
                }
                prev_field = field;
                result.Add(field, cell.Col);
            }
        }

        static void FixMissingSubheadersForMixedRealEstate(IAdapter adapter, ColumnOrdering columnOrdering)
        {
            //see DepEnergo2010.doc  in tests
            if (!columnOrdering.ContainsField(DeclarationField.MixedColumnWithNaturalText))
            {
                return;
            }
            var headerCell = adapter.GetDeclarationField(columnOrdering, columnOrdering.HeaderBegin.Value, DeclarationField.MixedColumnWithNaturalText);
            var subCells = FindSubcellsUnder(adapter, headerCell);
            if (subCells.Count != 3)
            {
                return;
            }
            for (int row = columnOrdering.FirstDataRow; row < adapter.GetRowsCount(); row++)
            {
                if (row > columnOrdering.FirstDataRow + 5) break;
                TColumnSpan middleCol = new TColumnSpan();
                middleCol.BeginColumn = subCells[1].Col; // we check only the  second column, todo check the  first one and  the third
                middleCol.EndColumn = subCells[2].Col;
                string areaStr = adapter.GetCell(row, middleCol.BeginColumn).GetText(true);
                if (!DataHelper.ParseSquare(areaStr).HasValue)
                {
                    return;
                }
            }
            columnOrdering.Add(DeclarationField.MixedRealEstateType, subCells[0].Col);
            columnOrdering.Add(DeclarationField.MixedRealEstateSquare, subCells[1].Col);
            columnOrdering.Add(DeclarationField.MixedRealEstateCountry, subCells[2].Col);
            columnOrdering.Delete(DeclarationField.MixedColumnWithNaturalText);
        }


        static void FixBadColumnName01(ColumnOrdering c)
        {
            //move MixedColumnWithNaturalText  to MixedRealEstateType
            if (!c.ContainsField(DeclarationField.MixedColumnWithNaturalText)) return;
            if (        c.ContainsField(DeclarationField.MixedRealEstateCountry)  
                    &&  c.ContainsField(DeclarationField.MixedRealEstateSquare)
                )
            {
                c.Add(DeclarationField.MixedRealEstateType, c.ColumnOrder[DeclarationField.MixedColumnWithNaturalText].BeginColumn);
                c.Delete(DeclarationField.MixedColumnWithNaturalText);
            }
        }


        static public ColumnOrdering ExamineHeader(IAdapter adapter)
        {
            ColumnOrdering columnOrdering = new ColumnOrdering();
            int headerStartRow = ProcessTitle(adapter, columnOrdering);
            int headerEndRow = headerStartRow + 1;
            var firstRow = adapter.GetCells(headerStartRow);

            int colCount = 0;
            bool headerCanHaveSecondLevel = true;
            foreach (var cell in firstRow)
            {
                string text = cell.GetText(true);
                Logger.Debug("column title: " + text);

                if (text == "")
                {
                    continue;
                }
                var subCells = FindSubcellsUnder(adapter, cell);

                if (subCells.Count() <= 1 || ! headerCanHaveSecondLevel)
                {
                    headerEndRow = Math.Max(headerEndRow, cell.Row + cell.MergedRowsCount);
                    if (!text.IsNullOrWhiteSpace())
                    {
                        DeclarationField field = HeaderHelpers.GetField(text.Replace('\n', ' '));
                        if (field == DeclarationField.None)
                        {
                            throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1}", headerStartRow, colCount));
                        }
                        columnOrdering.Add(field, cell.Col);
                        if (DeclarationField.NameOrRelativeType == field && cell.MergedRowsCount == 1)
                        {
                            string fioAfterHeader = adapter.GetDeclarationField(columnOrdering, headerEndRow, field).GetText(true);
                            headerCanHaveSecondLevel = fioAfterHeader.Length == 0;
                        }
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    SecondLevelHeader(adapter, cell, subCells, columnOrdering);
                    headerEndRow = Math.Max(headerEndRow, subCells[0].Row + subCells[0].MergedRowsCount);
                    colCount += cell.MergedColsCount;
                }
            }

            columnOrdering.HeaderBegin = headerStartRow;
            columnOrdering.HeaderEnd = headerEndRow;
            int firstDataRow = columnOrdering.HeaderEnd.Value;

            // пропускаем колонку с номерами
            string cellText1 = adapter.GetCell(firstDataRow, 0).GetText();
            string cellText2 = adapter.GetCell(firstDataRow, 1).GetText();
            if (cellText1 == "1" && cellText2 == "2")
            {
                firstDataRow++;
            }

            columnOrdering.FirstDataRow = firstDataRow;

            if (columnOrdering.ColumnOrder.Count() == 0)
            {
                throw new SmartParserException("cannot find headers");
            }
            FixMissingSubheadersForMixedRealEstate(adapter, columnOrdering);
            FixBadColumnName01(columnOrdering);
            return columnOrdering;
        }
    }
}
