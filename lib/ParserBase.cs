using System;
using System.Collections.Generic;
using System.Text;
using System.Globalization;

namespace Smart.Parser.Lib
{
    public class ParserBase
    {
        public static bool UseDecimalRawNormalization = false;
        public static NumberFormatInfo ParserNumberFormatInfo = new NumberFormatInfo();

        public ParserBase()
        {
            ParserNumberFormatInfo.NumberDecimalSeparator = ",";
        }

        public static string NormalizeRawDecimalForTest(string s)
        {

            if (!UseDecimalRawNormalization) return s;
            Double v;
            if (Double.TryParse(s, out v))
            {
                return v.ToString(ParserNumberFormatInfo);
            }
            else
            {
                return s.Replace(".", ",").Replace("\u202f", " ");
                //return s;
            }
        }


    }
}
