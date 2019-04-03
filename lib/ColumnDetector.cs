using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
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

            return (nonEmptyCellCount > 3) &&
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
            int auxRowCount = 0;
            

            while (!IsHeader(t.Rows[headerRowNum]))
            {
                headerRowNum++;

                if (headerRowNum >= t.GetRowsCount())
                {
                    throw new ColumnDetectorException(String.Format("Headers not found"));
                }
            }

            var header = t.Rows[headerRowNum];

            ColumnOrdering res = new ColumnOrdering();
            int colCount = 0;
            int index = 0;
            int headerRows = 1;
            foreach (var cell in header.Cells)
            {
                string text = cell.GetText(true);

                if (text == "")
                {
                    break;
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
                        res.Add(field, index);
                        index++;
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    auxRowCount = 1;
                    int span = cell.GridSpan == 0 ? 1 : cell.GridSpan;
                    int rowSpan = cell.MergedRowsCount;
                    Row auxRow = t.Rows[headerRowNum + rowSpan];
                    var auxCellsIter = auxRow.Cells.GetEnumerator();
                    auxCellsIter.MoveNext();
                    int auxColCount = 0;

                    field = DeclarationField.None;
                    while (auxColCount < colCount + span)
                    {
                        var auxCell = auxCellsIter.Current;
                        if (auxColCount >= colCount)
                        {
                            string cellText = auxCell.GetText(true);

                            //  пустая колонка страны (предыдущая колонка - площадь
                            if (cellText == "" && field == DeclarationField.StatePropertyArea)
                            {
                                field = DeclarationField.StatePropertyCountry;
                            }
                            else
                            {
                                string fullText = text + " " + cellText;
                                field = HeaderHelpers.TryGetField(fullText);
                            }


                            if (field == DeclarationField.None)
                            {
                                throw new ColumnDetectorException(String.Format("Fail to detect column type row: {0} col:{1} text:'{2}'", headerRowNum + 1, auxColCount, cellText));
                            }
                            res.Add(field, index);
                            index++;
                        }

                        auxCellsIter.MoveNext();
                        int auxSpan = auxCell.GridSpan == 0 ? 1 : auxCell.GridSpan;
                        auxColCount += auxSpan;
                    }

                    colCount += cell.GridSpan;
                }

            }

            int firstDataRow = headerRowNum + headerRows;// + auxRowCount;
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
