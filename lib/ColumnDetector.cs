using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
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

            string[] title_words = { "сведения", "обязательствах", "доход", "период"};
            bool has_title_words = Array.Exists(title_words, s => text.Contains(s));
            if (!has_title_words)
                return false;

            text = Regex.Replace(text, "8\\s+июля\\s+2013", "");
            var matches = Regex.Matches(text, @"\b20\d\d\b");

            if (matches.Count > 0 )
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

        static private bool IsHeader(Row r)
        {
            var cells = r.Cells;
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

        static int ProcessTitle(IAdapter adapter, ColumnOrdering res)
        {
            int row = 0;
            string title = null;
            string ministry = null;
            int? year = null;

            bool findTitle = false;
            while (true)
            {
                Row currRow = adapter.Rows[row];
                string section_text;
                bool isSection = adapter.IsSectionRow(currRow, out section_text);
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
                        res.Section = section_text;
                    }
                }
                else if (IsHeader(currRow))
                    break;

                row +=  1;

                if (row >= adapter.GetRowsCount())
                {
                    throw new ColumnDetectorException(String.Format("Headers not found"));
                }
            }
            if (!findTitle) {
                if (GetValuesFromTitle(adapter.GetTitle(), ref title, ref year, ref ministry))
                {
                    findTitle = true;
                }
            }

            if (findTitle)
            {
                res.Title = title;
                res.Year = year;
                res.MinistryName = ministry;
            }
            return row;
        }
        static List<Cell> FindSubcellsUnder(IAdapter adapter, Cell cell)
        {
            Row underRow = adapter.Rows[cell.Row + cell.MergedRowsCount];
            var subCells = new List<Cell>();
            foreach (var underCell in underRow.Cells)
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
                    throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1} text:'{2}'", cell.Row,cell.Col, fullText));
                }
                prev_field = field;
                result.Add(field, cell.Col);
            }
        }

        
        static public ColumnOrdering ExamineHeader(IAdapter adapter)
        {
            ColumnOrdering res = new ColumnOrdering();
            int headerStartRow = ProcessTitle(adapter, res);
            int headerEndRow = headerStartRow + 1;
            var firstRow = adapter.Rows[headerStartRow];

            int colCount = 0;

            foreach (var cell in firstRow.Cells)
            {
                string text = cell.GetText(true);
                Logger.Debug("column title: " + text);

                if (text == "")
                {
                    continue;
                }
                var subCells = FindSubcellsUnder(adapter, cell);

                if (subCells.Count() <= 1)
                {
                    headerEndRow = Math.Max(headerEndRow, cell.Row + cell.MergedRowsCount);
                    if (!text.IsNullOrWhiteSpace())
                    {
                        DeclarationField field = HeaderHelpers.GetField(text.Replace('\n', ' '));
                        if (field == DeclarationField.None)
                        {
                            throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1}", headerStartRow, colCount));
                        }
                        res.Add(field, cell.Col);
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    SecondLevelHeader(adapter, cell, subCells, res);
                    headerEndRow = Math.Max(headerEndRow, subCells[0].Row + subCells[0].MergedRowsCount);
                    colCount += cell.MergedColsCount;
                }
            }

            res.HeaderBegin = headerStartRow;
            res.HeaderEnd = headerEndRow;
            int firstDataRow = res.HeaderEnd.Value;

            // пропускаем колонку с номерами
            string cellText1 = adapter.GetCell(firstDataRow, 0).GetText();
            string cellText2 = adapter.GetCell(firstDataRow, 1).GetText();
            if (cellText1 == "1" && cellText2 == "2")
            {
                firstDataRow++;
            }

            res.FirstDataRow = firstDataRow;

            if (res.ColumnOrder.Count() == 0)
            {
                throw new SmartParserException("cannot find headers");
            }

            return res;
        }
    }
}
