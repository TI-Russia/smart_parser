using Parser.Lib;
using static Parser.Lib.SmartParserException;
using System;
using System.Collections.Generic;
using System.Linq;
using Smart.Parser.Lib;
using TI.Declarator.ParserCommon;
using System.Text.RegularExpressions;

namespace Smart.Parser.Adapters
{
    public class Cell 
    {
        public int Row = -1;
        public int Col = -1; // not merged column index
        public int CellWidth = 0; // in pixels
        public int AdditTableIndention = 0; // only for Word: http://officeopenxml.com/WPtableIndent.php
        public string FontName = null;
        public int FontSize = 0;

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
                if (DataHelper.IsEmptyValue(text))
                {
                    return "";
                }
            }

            return text;
        }
        public override string ToString()
        {
            return Text;
        }
        public string[] SplitJoinedLinesByFuzzySeparator(List<int> linesWithNumbers)
        {
            var value = GetText(); // no trim
            string[] lines;

            // Eg: "1. Квартира\n2. Квартира"
            if (Regex.Matches(value, @"^\d\.\s+.+\n\d\.\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"\d\.\s").Skip(1).ToArray();
                return lines;
            }

            // a weaker regexp but the same count
            if (Regex.Matches(value, @"^\s*\d\.\s*.+\n\d\.\s*", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"\d+\s*\.").Skip(1).ToArray();
                if (lines.Length == linesWithNumbers.Count && linesWithNumbers.Count > 0)
                {
                    return lines;
                }

            }

            // Eg: "- Квартира\n- Квартира"
            if (Regex.Matches(value, @"^\p{Pd}\s+.+\n\p{Pd}\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"\n\p{Pd}");
                return lines;
            }

            // Eg: "... собственность) - Жилой дом ..."
            if (Regex.Matches(value, @"^\p{Pd}.+\)[\s\n]+\p{Pd}\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"[\s\n]\p{Pd}\s");
                return lines;
            }

            // Eg: "Квартира \n(долевая собственность \n\n0,3) \n \n \n \nКвартира \n(индивидуальная собственность) \n"
            var matches = Regex.Matches(value, @"[^\)]+\([^\)]+\)\;?", RegexOptions.Singleline);
            if (matches.Count == linesWithNumbers.Count && linesWithNumbers.Count > 0)
            {
                lines = matches.Select(m => m.Value).ToArray();
                return lines;
            }

            // Eg: Квартира\n\nКвартира\n\nКвартира
            var value1 = Regex.Replace(value, @"[\s-[\n]]+\n", "\n");
            var tokens = Regex.Split(value1, @"\n\n+", RegexOptions.Singleline);
            if (tokens.Length == linesWithNumbers.Count && linesWithNumbers.Count > 0)
            {
                return tokens;
            }

            lines = value.Trim(' ', ';').Split(';');
            if (lines.Length == linesWithNumbers.Count)
            {
                return lines;
            }
            lines = value.Split('\n');
            if (lines.Length == linesWithNumbers.Count)
            {
                return lines;
            }

            var notEmptyLines = new List<string>();
            foreach (var l in lines)
            {
                if (l.Trim(' ').Length > 0)
                {
                    notEmptyLines.Add(l);
                }
            }
            if (notEmptyLines.Count == linesWithNumbers.Count)
            {
                return notEmptyLines.ToArray();
            }

            TStringMeasure.InitDefaultFont(FontName, FontSize);
            lines = TStringMeasure.GetLinesBySoftBreaks(value, CellWidth).ToArray();
            var items = new List<String>();
            for (int i = 0; i < linesWithNumbers.Count; i++)
            {
                int start = linesWithNumbers[i];
                int end = lines.Length;
                if (i + 1 < linesWithNumbers.Count)
                {
                    end = linesWithNumbers[i + 1];
                }

                var item = String.Join("\n", lines.Skip(start).Take(Math.Min(end, lines.Length) - start)).ReplaceEolnWithSpace();
                items.Add(item);
                if (end >= lines.Length)
                {
                    break;
                }
            }
            return items.ToArray();
        }


    };

}
