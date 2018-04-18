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

        public static string RemoveStupidTranslit(this string str)
        {
            return str.Replace('C', 'С').Replace('c', 'с');
        }
    }
}
