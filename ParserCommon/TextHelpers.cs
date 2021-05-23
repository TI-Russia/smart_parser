using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace TI.Declarator.ParserCommon
{
    public static class TextHelpers
    {
        private static readonly CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        public static decimal ParseDecimalValue(this string val)
        {
            var processedVal = Regex.Replace(val, @"\s+", string.Empty);
            return !decimal.TryParse(processedVal, NumberStyles.Any, RussianCulture, out var res) && !decimal.TryParse(processedVal, NumberStyles.Any, CultureInfo.InvariantCulture, out res)
                ? throw new Exception($"can't parse value '{processedVal}' as decimal")
                : res;
        }

        public static bool IsNullOrWhiteSpace(this string str) => string.IsNullOrWhiteSpace(str);

        /// <summary>
        /// Extracts a four-digit representation of year from given string
        /// and converts it to an integer.
        /// </summary>
        /// <param name="str"></param>
        /// <returns></returns>
        private static readonly Regex ExtractYearRegex = new Regex("[0-9]{4}", RegexOptions.Compiled);

        public static int? ExtractYear(string str)
        {
            var m = ExtractYearRegex.Match(str);
            if (m.Success)
            {
                var year = int.Parse(m.Groups[0].Value);
                return year > DateTime.Today.Year || year < 1980 ? null : (int?)year;
            }
            else
            {
                return null;
            }
        }

        private static readonly IReadOnlyList<(char from, char to)> TranslitCharacters = new[] {
            ('A', 'А'), ('a', 'а'),
            ('C', 'С'), ('c', 'с'),
            ('E', 'Е'), ('e', 'е'),
            ('M', 'М'),
            ('O', 'О'), ('o', 'о'),
            ('P', 'Р'), ('p', 'р'),
            ('T', 'Т'),
            ('X', 'Х'), ('x', 'х'),
        };
        /// <summary>
        /// Replaces Latin characters that accidentally found their way into Russian words
        /// with their Cyrillic counterparts. Use with caution.
        /// </summary>
        /// <param name="str"></param>
        /// <returns></returns>
        public static string RemoveStupidTranslit(this string str)
        {
            var builder = new StringBuilder(str);
            foreach (var (from, to) in TranslitCharacters)
            {
                builder.Replace(from, to);
            }
            return builder.ToString();
        }

        public static string ReplaceEolnWithSpace(this string str)
        {
            return str.Replace('\n', ' ').Trim();
        }

        public static string CoalesceWhitespace(this string str)
        {
            return Regex.Replace(str, @"[\s-[\n]]+", " ");
        }

        public static string NormSpaces(this string str)
        {
            if (str == null)
            {
                return null;
            }
            return str.ReplaceEolnWithSpace().CoalesceWhitespace().Trim();
        }

        public static string ReplaceFirst(this string str, string substr, string replStr)
        {
            var replRegex = new Regex(Regex.Escape(substr));
            return replRegex.Replace(str, replStr, 1);
        }

        public static bool CanBeInitials(string s) => Regex.Match(s.Trim(), @"\w\.\w\.").Success;

        private static readonly string[] PatronymicSuffixStrings = { "вич", "вна", "вной", "внва", "вны", "тич", "мич", "ьич", "ьича", "ьича", "вича", "тича", "мича", "чны", "чна", "ьичем", "тичем", "мичем", "вичем", "чной", "вной" };

        public static bool  CanBePatronymic(string s)
        {
            s = s.Replace("-", string.Empty);
            if (s.IsNullOrWhiteSpace())
            {
                return false;
            }
            if (char.IsUpper(s[0]) && s.EndsWith(".") && s.Length == 4 && s[1] == '.')
            {
                //"А.Б."
                return true;
            }
            return char.IsUpper(s[0]) && (s.EndsWithAny(PatronymicSuffixStrings) || (s.Length <= 4 && s.EndsWith("."))) /* в., в.п., вяч. */;
        }

        private static readonly string[] RoleStrings = { 
            "заместител", "начальник", "аудитор", "депутат", 
            "секретарь", "уполномоченный", "председатель", "бухгалтер", "руководител", "глава", "главы", "заведующий",
            "заведующая", "служащий", "служащая"
            };

        public static bool MayContainsRole(string s)
        {
            s = s.OnlyRussianLowercase();
            return !s.IsNullOrWhiteSpace() && s.ContainsAny(RoleStrings);
        }

        public static string RemoveCharacters(this string source, params char[] patterns)
        {
            if (source.IndexOfAny(patterns) < 0)
            {
                return source;
            }
            return new string(source.Where(c => Array.IndexOf(patterns, c) < 0).ToArray());
        }

        public static bool EndsWithAny(this string source, params string[] patterns) => patterns.Any(pattern => source.EndsWith(pattern, StringComparison.OrdinalIgnoreCase));

        public static bool StartsWithAny(this string source, params string[] patterns) => patterns.Any(pattern => source.StartsWith(pattern, StringComparison.OrdinalIgnoreCase));

        public static bool ContainsAny(this string source, params string[] patterns) => patterns.Any(pattern => source.Contains(pattern, StringComparison.OrdinalIgnoreCase));

        public static bool ContainsAll(this string source, params string[] patterns) => patterns.All(pattern => source.Contains(pattern, StringComparison.OrdinalIgnoreCase));

        public static string[] SplitByEmptyLines(string value)
        {
            string[] lines = Regex.Split(value, @"\n\s*\n").ToArray();
            return lines;
        }


        public static string SliceArrayAndTrim(string[] lines, int start, int end)
        {
            return String.Join("\n", lines.Skip(start).Take(end - start)).ReplaceEolnWithSpace();
        }



    }
}