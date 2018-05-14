using System;
using System.Globalization;

namespace TI.Declarator.ParserCommon
{
    public static class TextHelpers
    {
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");
        public static decimal ParseDecimalValue(this string val)
        {
            decimal res;
            string processedVal = val.Replace(" ", "");
            try
            {
                res = Decimal.Parse(processedVal, RussianCulture);
            }
            catch (FormatException fEx)
            {
                res = Decimal.Parse(processedVal, CultureInfo.InvariantCulture);
            }

            return res;
        }

        public static bool IsNullOrWhiteSpace(this string str)
        {
            return String.IsNullOrWhiteSpace(str);
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
    }
}
