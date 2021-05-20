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
            //TStringMeasure.InitGraphics("Liberation Serif", 10);
            TStringMeasure.InitGraphics("FreeSerif", 10);
            float width = TStringMeasure.MeasureStringWidth("__________", 1.0F);
            Assert.AreEqual(40, (int)width);

            width = TStringMeasure.MeasureStringWidth("0123456789", 1.0F);
            Assert.AreEqual(40, (int)width);

            width = TStringMeasure.MeasureStringWidth("шШщЩюЮжЖ", 1.0F);
            Assert.AreEqual(48, (int)width);

            width = TStringMeasure.MeasureStringWidth("тест текст");
            Assert.AreEqual(34, (int)width);
        }


    }
}
