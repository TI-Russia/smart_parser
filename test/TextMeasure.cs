using Microsoft.VisualStudio.TestTools.UnitTesting;
using SmartParser.Lib;
using StringHelpers;
using System.IO;
using SmartParser.Lib;
using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace test
{
    [TestClass]
    public class StringMeasureTest
    {

        static Dictionary<string, int> CasesTimesNewRoman10_Approximated = new Dictionary<string, int>
{
    {"_", 3},
    {"__", 6},
    {"a", 2},
    {"aa", 5},
    {"__________", 33},
    {"_        _", 33},
    {",.,,..,.,.", 16},
    {"0123456789", 33},
    {"тест текст", 30},
    {"шШщЩюЮжЖ", 46},
};
        static Dictionary<string, int> CasesTimesNewRoman10_SkiaSharp = new Dictionary<string, int>
{
    {"_", 5},
    {"__", 10},
    {"a", 4},
    {"aa", 9},
    {"__________", 50},
    {"_        _", 50},
    {",.,,..,.,.", 25},
    {"0123456789", 50},
    {"тест текст", 45},
    {"шШщЩюЮжЖ", 69},
};
        [TestMethod]
        public void UpdateExpectedValuesTimesNewRoman10()
        {
            TStringMeasure.InitDefaultFontSystem("Times New Roman", 10);
            Console.WriteLine("Updating expected values based on SkiaSharp measurements:");

            foreach (var testCase in CasesTimesNewRoman10_SkiaSharp.Keys)
            {
                float width = TStringMeasure.MeasureStringWidth(testCase);
                int roundedWidth = (int)Math.Round(width);
                Console.WriteLine($"String: '{testCase}', New Expected Width: {roundedWidth}");
                CasesTimesNewRoman10_SkiaSharp[testCase] = roundedWidth;
            }
        }

        [TestMethod]
        public void TimesNewRomanCharWidthWindows()
        {
            if (!TStringMeasure.IsLinux())
            {
                // there is no "Times New Roman" under ubuntu
                TStringMeasure.InitDefaultFontSystem("Times New Roman", 10);
                foreach (var i in CasesTimesNewRoman10_SkiaSharp)
                {
                    float width = TStringMeasure.MeasureStringWidth(i.Key);
                    Assert.AreEqual(i.Value, (int)Math.Round(width), $"Mismatch for string '{i.Key}'. Expected: {i.Value}, Actual: {width}");

                }
            }
        }

        [TestMethod]
        public void TextMeasureApproximatedTest()
        {
            TStringMeasure.InitDefaultFontApproximated("Times New Roman", 10);
            foreach (var i in CasesTimesNewRoman10_Approximated)
            {
                float width = TStringMeasure.MeasureStringWidth(i.Key);
                Assert.AreEqual(i.Value, (int)width);
            }
        }
    }
}
