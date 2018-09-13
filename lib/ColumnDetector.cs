using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    public class ColumnDetector
    {
        static private bool IsHeader(Row r)
        {
            var cells = r.Cells;
            string text = "";
            foreach (var cell in cells)
            {
                text += cell.GetText();
            }

            if (text.Trim() == "")
            {
                return false;
            }

            return (cells.Count > 2) &&
                   (cells.First().GetText(true) != "1");
        }

        static public ColumnOrdering ExamineHeader(IAdapter t)
        {
            int headerRowNum = 0;
            int auxRowCount = 0;

            while (!IsHeader(t.Rows[headerRowNum]))
            {
                headerRowNum++;
            }

            var header = t.Rows[headerRowNum];

            ColumnOrdering res = new ColumnOrdering();
            int colCount = 0;
            int index = 0;
            foreach (var cell in header.Cells)
            {
                string text = cell.GetText(true);

                DeclarationField field;
                if (cell.GridSpan <= 1)
                {
                    if (!text.IsNullOrWhiteSpace())
                    {
                        field = HeaderHelpers.GetField(text.Replace('\n', ' '));
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
                    Row auxRow = t.Rows[headerRowNum+1];
                    var auxCellsIter = auxRow.Cells.GetEnumerator();
                    auxCellsIter.MoveNext();
                    int auxColCount = 0;

                    while (auxColCount < colCount + span)
                    {
                        var auxCell = auxCellsIter.Current;
                        if (auxColCount >= colCount)
                        {
                            string fullText = text + " " + auxCell.GetText(true);
                            field = HeaderHelpers.GetField(fullText);
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

            res.FirstDataRow = headerRowNum + 1 + auxRowCount;

            return res;
        }
    }
}
