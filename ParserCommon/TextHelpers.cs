using System;
using System.Globalization;
using System.Text.RegularExpressions;

namespace TI.Declarator.ParserCommon
{
    public static class TextHelpers
    {
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");
        private static Regex YearRegexString = new Regex("[0-9]{4}");
        public static decimal ParseDecimalValue(this string val)
        {
            decimal res;
            string processedVal = val.Replace(" ", "");
            if (!Decimal.TryParse(processedVal, NumberStyles.Any, RussianCulture, out res))
            {
                if (!Decimal.TryParse(processedVal, NumberStyles.Any, CultureInfo.InvariantCulture, out res))
                {
                    throw new Exception("can't parse value '" + processedVal + "' as decimal");
                }
            }
            

            return res;
        }

        public static bool IsNullOrWhiteSpace(this string str)
        {
            return String.IsNullOrWhiteSpace(str);
        }

        /// <summary>
        /// Extract a four-digit representation of year from given string
        /// and converts it to an integer
        /// </summary>
        /// <param name="str"></param>
        /// <returns></returns>
        public static int? ExtractYear(this string str)
        {
            Match m = YearRegexString.Match(str);
            if (m.Success)
            {
                return Int32.Parse(m.Groups[0].Value);
            }
            else return null;
        }

        /// <summary>
        /// Replaces Latin characters that accidentally found their way into Russian words
        /// with their Cyrillic counterparts. Use with caution.
        /// </summary>
        /// <param name="str"></param>
        /// <returns></returns>
        public static string RemoveStupidTranslit(this string str)
        {
            return str.Replace('A', 'А').Replace('a', 'а')
                      .Replace('C', 'С').Replace('c', 'с')
                      .Replace('E', 'Е').Replace('e', 'е')
                      .Replace('M', 'М')
                      .Replace('O', 'О').Replace('o', 'о')
                      .Replace('P', 'Р').Replace('p', 'р')
                      .Replace('T', 'Т')
                      .Replace('X', 'Х').Replace('x', 'х');
        }

        public static string CleanWhitespace(this string str)
        {
            return str.Replace('\n', ' ').Trim();
        }
    }
}
