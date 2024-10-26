using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using NPOI.SS.Formula.Functions;
using System.Text.RegularExpressions;


namespace SmartParser.Lib
{
    public class TSectionPredicate
    {
        List<Cell> Cells;
        int ColsCount;
        bool PrevRowIsSection;
        bool HasInnerBorders;
        public TSectionPredicate(List<Cell> cells, int colsCount, bool prevRowIsSection, bool hasInnerBorders)
        {
            Cells = cells;
            ColsCount = colsCount;
            PrevRowIsSection = prevRowIsSection;
            HasInnerBorders = hasInnerBorders;
        }
        static bool CheckSectionLanguageModel(string cellText)
        {
            if (cellText.Contains("Сведения о"))
            {
                return true;
            }

            if (cellText.StartsWith("за", StringComparison.OrdinalIgnoreCase) && cellText.EndsWith("год", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            // first words: get it from previous results:
            // ~/media/json$ ls | xargs  jq -cr '.persons[].person.department' | awk '{print $1}' | sort | uniq -c  | sort -nr
            // стоит перейти на более продвинутую модель на триграммах
            if (cellText.StartsWith("ФК") ||
                    cellText.StartsWith("ФГ") ||
                    cellText.StartsWith("ГУ") ||
                    cellText.StartsWith("федеральн", StringComparison.OrdinalIgnoreCase) ||
                    cellText.StartsWith("ФБУ") ||
                    cellText.StartsWith("Руководство") ||
                    cellText.StartsWith("ФАУ") ||
                    cellText.StartsWith("Департамент") ||
                    cellText.StartsWith("Заместители") ||
                    cellText.StartsWith("Институт") ||
                    cellText.StartsWith("Государственное") ||
                    cellText.StartsWith("Главное") ||
                    cellText.StartsWith("Отдел") ||
                    cellText.StartsWith("Управлени") ||
                    cellText.StartsWith("Фонд") ||
                    cellText.StartsWith("АНО") ||
                    cellText.StartsWith("УФСИН") ||
                    cellText.StartsWith("Центр") ||
                    cellText.StartsWith("ФСИН") ||
                    cellText.StartsWith("Министерств") ||
                    cellText.StartsWith("Лица") ||
                    cellText.StartsWith("ИК") ||
                    cellText.StartsWith("Филиал") ||
                    cellText.StartsWith("информация о", StringComparison.OrdinalIgnoreCase))


            {
                return true;
            }
            return false;
        }

        public string? GetSectionText()
        {
            if (Cells.Count == 0)
            {
                return null;
            }
            int maxMergedCols = 0;
            int maxCellWidth = 0;
            string rowText = "";
            string cellText = "";
            int cellsWithTextCount = 0;
            int allWidth = 0;
            foreach (var c in Cells)
            {
                string trimmedText = c.Text.Trim(' ', '\n');
                if (c.MergedColsCount > maxMergedCols)
                {
                    cellText = trimmedText;
                    maxMergedCols = c.MergedColsCount;
                };
                if (trimmedText.Length > 0)
                {
                    rowText += c.Text;
                    cellsWithTextCount++;
                    if (c.CellWidth > maxCellWidth)
                    {
                        maxCellWidth = c.CellWidth;
                    }
                }
                allWidth += c.CellWidth;

            }
            rowText = rowText.Trim(' ', '\n');
            bool manyColsAreMerged = maxMergedCols > ColsCount * 0.45;
            bool OneColumnIsLarge = maxCellWidth > 1000 || maxCellWidth >= allWidth * 0.3;
            bool langModel = CheckSectionLanguageModel(cellText);
            bool hasEnoughLength = rowText.Length >= 9; // "Референты"; но встречаются ещё "Заместители Министра"
            bool halfCapitalLetters = rowText.Count(char.IsUpper) * 2 > rowText.Length;

            // Stop Words
            List<string> stopWords = new List<string> { "сведения" };
            bool hasStopWord = false;
            foreach (var word in stopWords)
            {
                if (rowText.ToLower() == word) hasStopWord = true;
            }
            if (hasStopWord) return null;
            if (!HasInnerBorders)
            {
                return rowText;
            }

            // "ННИИПК", "СамГМУ"  
            if (!hasEnoughLength && !halfCapitalLetters)
            {
                return null;
            }
            if (Regex.Match(rowText, @"период с.*20\d\d\s*г.").Success)
            {
                return rowText;
            }

            if (!OneColumnIsLarge)
            {
                return null;
            }

            if (cellsWithTextCount == 1)
            {
                // possible title, exact number of not empty columns is not yet defined
                if (maxMergedCols >= 4 && langModel)
                {
                    return rowText;
                };
                if (manyColsAreMerged)
                {
                    return rowText;
                }
            }
            if (cellsWithTextCount <= 2)
            {
                if (manyColsAreMerged && langModel)
                {
                    return cellText;
                }
            }

            // в начале могут быть многострочные заголовки, которые обычно начинаются с маленькой буквы
            if (PrevRowIsSection && hasEnoughLength && Cells[0].Row < 10)
            {
                if (char.IsLower(rowText[0]))
                {
                    return rowText;
                }
            }
            return null;
        }

    }
}
