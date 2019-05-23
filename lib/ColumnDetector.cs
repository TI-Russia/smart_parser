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
        static public bool IsSection(Row r, out string text)
        {
            text = null;
            if (r.Cells.Count == 0)
            {
                return false;
            }
            int merged_row_count = r.Cells[0].MergedRowsCount;
            int cell_count = r.Cells.Count();

            if (merged_row_count > 1)
            {
                return false;
            }

            int merged_col = r.Cells[0].MergedColsCount;
            if (merged_col < 5)
            {
                return false;
            }

            text = r.Cells[0].GetText(true);

            return true;
        }

        static public bool IsTitle(Row r, ref string title, ref int? year, ref string ministry)
        {
            //title = null;
            //year = null;
            //ministry = null;
            int cell_count = r.Cells.Count();
            if (cell_count == 0)
                return false;
            int merged_row_count = r.Cells[0].MergedRowsCount;
            string text = r.Cells[0].GetText(true);

            int merged_col_count = r.Cells[0].MergedColsCount;

            if (merged_col_count < 5)
                return false;

            int text_len = text.Length;

            if (text_len < 20)
                return false;

            if (title == null)
                title = text;
            else
                title += " " + text;

            string[] title_words = { "сведения", "обязательствах", "доходах", "период" };
            bool has_title_words = Array.Exists(title_words, s => text.Contains(s));

            if (!has_title_words)
                return false;

            var matches = Regex.Matches(text, @"\b20\d\d\b");

            if (matches.Count >= 2 )
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
        static private bool IsEmptyRow(Row r)
        {
            var cells = r.Cells;
            string text = "";
            foreach (var cell in cells)
            {
                text += cell.GetText();
            }

            return (text.Trim() == "");
        }

        static public ColumnOrdering ExamineHeader(IAdapter t)
        {
            int headerRowNum = 0;
            ColumnOrdering res = new ColumnOrdering();

            string title = null;
            string ministry = null;
            int? year = null;

            bool findTitle = false;
            while (true)
            {
                string section_text;
                if (IsTitle(t.Rows[headerRowNum], ref title, ref year, ref ministry))
                {
                    findTitle = true;
                }
                else if (IsSection(t.Rows[headerRowNum], out section_text))
                {
                    res.Section = section_text;
                }
                if (IsHeader(t.Rows[headerRowNum]))
                    break;

                headerRowNum++;

                if (headerRowNum >= t.GetRowsCount())
                {
                    throw new ColumnDetectorException(String.Format("Headers not found"));
                }
            }

            if (findTitle)
            {
                res.Title = title;
                res.Year = year;
                res.MinistryName = ministry;
            }

            var header = t.Rows[headerRowNum];

            int colCount = 0;
            int index = 0;
            int headerRows = 1;
            foreach (var cell in header.Cells)
            {
                string text = cell.GetText(true);

                if (text == "")
                {
                    continue;
                }

                if (cell.MergedRowsCount > 1)
                {
                    headerRows = Math.Max(headerRows, cell.MergedRowsCount);
                }

                DeclarationField field;
                if (cell.MergedColsCount <= 1)
                {
                    if (!text.IsNullOrWhiteSpace())
                    {
                        field = HeaderHelpers.GetField(text.Replace('\n', ' '));
                        if (field == DeclarationField.None)
                        {
                            throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1}", headerRowNum, colCount));
                        }
                        res.Add(field, cell.Col);
                        index++;
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    int span = cell.GridSpan == 0 ? 1 : cell.GridSpan;
                    int rowSpan = cell.MergedRowsCount;
                    Row auxRow = t.Rows[headerRowNum + rowSpan];
                    var auxCellsIter = auxRow.Cells.GetEnumerator();
                    //auxCellsIter.MoveNext();
                    //int auxColCount = 0;

                    field = DeclarationField.None;
                    while (auxCellsIter.MoveNext()/* auxColCount < colCount + span*/)
                    {
                        var auxCell = auxCellsIter.Current;
                        if (auxCell.Col < cell.Col)
                            continue;
                        if (auxCell.Col >= cell.Col + cell.GridSpan)
                            break;



                        //if (auxColCount >= colCount)
                        {
                            string cellText = auxCell.GetText(true);
                            string fullText = text + " " + cellText;

                            //  пустая колонка страны (предыдущая колонка - площадь
                            if (cellText == "" && field == DeclarationField.StatePropertyArea)
                            {
                                field = DeclarationField.StatePropertyCountry;
                            }
                            else
                            {
                                field = HeaderHelpers.TryGetField(fullText);
                            }


                            if (field == DeclarationField.None)
                            {
                                throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1} text:'{2}'", auxCell.Row, auxCell.Col, cellText));
                            }
                            res.Add(field, auxCell.Col);
                            index++;
                        }

                        //auxCellsIter.MoveNext();
                        //int auxSpan = auxCell.GridSpan == 0 ? 1 : auxCell.GridSpan;
                        //auxColCount += auxSpan;
                    }

                    colCount += cell.GridSpan;
                }

            }

            int firstDataRow = headerRowNum + headerRows;

            // пропускаем колонку с номерами
            string cellText1 = t.GetCell(firstDataRow, 0).GetText();
            string cellText2 = t.GetCell(firstDataRow, 1).GetText();
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
