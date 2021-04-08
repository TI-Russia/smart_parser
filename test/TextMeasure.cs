using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using System.IO;
using Smart.Parser.Lib;
using static Algorithms.LevenshteinDistance;
using System;

namespace test
{
    [TestClass]
    public class StringMeasureTest
    {
        
        [TestMethod]
        public void TextMeasureTest()
        {
            string s2 = "тест текст";
            TStringMeasure.InitGraphics("Liberation Serif", 10);
            float width = TStringMeasure.MeasureStringWidth(s2);
            Assert.AreEqual(31, (int)width);
        }

           
    }
}
