using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Adapters
{
    //using Smart.Parser.Row;
    public class TSectionPredicates
    {
        static bool CheckSectionLanguageModel(string cellText)
        {
            if (cellText.Contains("Сведения о"))
            {
                return true;
            }
            if (cellText.StartsWith("Федеральн") ||
                cellText.StartsWith("ФКУ") ||
                cellText.StartsWith("ФГУП") ||
                cellText.StartsWith("ФБУ") ||
                cellText.StartsWith("Руководство") ||
                cellText.StartsWith("ФАУ") ||
                cellText.StartsWith("Департамент") ||
                cellText.StartsWith("Заместители") ||
                cellText.StartsWith("Институт") ||
                cellText.StartsWith("ФГБУ") ||
                cellText.StartsWith("Государственное") ||
                cellText.StartsWith("Фонд") ||
                cellText.StartsWith("АНО")
                )
            {
                return true;
            }
            return false;
        }

        public static bool IsSectionRow(Smart.Parser.Adapters.Row r, bool prevRowIsSection, int colsCount, out string text)
        {
            text = null;
            if (r.Cells.Count == 0)
            {
                return false;
            }
            int maxMergedCols = 0;
            string rowText = "";
            string cellText = "";
            int cellsWithTextCount = 0;
            foreach (var c in r.Cells)
            {
                string trimmedText = c.Text.Trim(' ', '\n');
                if (c.MergedColsCount > maxMergedCols)
                {
                    cellText = trimmedText;
                    maxMergedCols = c.MergedColsCount;
                }
                if (trimmedText.Length > 0)
                {
                    rowText += c.Text;
                    cellsWithTextCount++;
                }
            }
            rowText = rowText.Trim(' ', '\n');
            bool manyColsAreMerged = maxMergedCols > colsCount * 0.7;
            bool hasEnoughLength = rowText.Length > 10; // "Руководство";
            bool langModel = CheckSectionLanguageModel(cellText);
            if (!hasEnoughLength)
            {
                return false;
            }

            if (cellsWithTextCount == 1)
            {
                // possible title, exact number of not empty columns is not yet defined
                if (maxMergedCols > 5 && langModel)
                {
                    text = rowText;
                    return true;
                };
                if (manyColsAreMerged)
                {
                    text = rowText;
                    return true;
                }
            }
            if (cellsWithTextCount <= 2)
            {
                if (manyColsAreMerged && langModel)
                {
                    text = cellText;
                    return true;
                }
            }

            // в начале могут быть многострочные заголовки, которые обычно начинаются с маленькой буквы
            if (prevRowIsSection && hasEnoughLength && r.Cells[0].Row < 10)
            {
                if (char.IsLower(rowText[0]))
                {
                    text = rowText;
                    return true;
                }
            }
            return false;
        }

    }
}
