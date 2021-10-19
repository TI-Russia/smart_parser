using Microsoft.VisualStudio.TestTools.UnitTesting;
using SmartParser.Lib;
using StringHelpers;
using System.IO;
using SmartParser.Lib;
using System;
using System.Collections.Generic;

namespace test
{
    [TestClass]
    public class StringMeasureTest
    {

        static Dictionary<string, int> CasesTimesNewRoman10 = new Dictionary<string, int>
        {
            {"_", 3},
            {"__", 6},
            {"a", 2}, //2.95
            {"aa", 5},
            {"__________", 33},
            {"_        _", 33},
            {",.,,..,.,.", 16},
            {"0123456789", 33},
            {"тест текст", 30},
            {"шШщЩюЮжЖ", 46},
            //{"гараж (долевое участие в строительстве),", 124},
        };

        [TestMethod]
        public void TimesNewRomanCharWidthWindows()
        {
            if (!TStringMeasure.IsLinux())
            {
                // there is no "Times New Roman" under ubuntu
                TStringMeasure.InitDefaultFontSystem("Times New Roman", 10);
                foreach (var i in CasesTimesNewRoman10)
                {
                    float width = TStringMeasure.MeasureStringWidth(i.Key);
                    Assert.AreEqual(i.Value, (int)width);
                }
            }
        }

        [TestMethod]
        public void TextMeasureApproximatedTest()
        {
            TStringMeasure.InitDefaultFontApproximated("Times New Roman", 10);
            foreach (var i in CasesTimesNewRoman10)
            {
                float width = TStringMeasure.MeasureStringWidth(i.Key);
                Assert.AreEqual(i.Value, (int)width);
            }
        }
    }
}
