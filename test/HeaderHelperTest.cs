﻿using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using System.IO;
using Smart.Parser.Lib;
using static Algorithms.LevenshteinDistance;

namespace test
{
    [TestClass]
    public class HeaderHelperTest
    {
        [TestMethod]
        public void HeaderHelperTest1()
        {
            string docFile = Path.Combine(TestUtil.GetTestDataPath(), "E - min_sport_2012_Rukovoditeli_gospredpriyatij,_podvedomstvennyih_ministerstvu.doc");
            //IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            IAdapter adapter = AsposeDocAdapter.CreateAdapter(docFile);
        }

        [TestMethod]
        public void StringComparisonTest()
        {
            string s1 = "собствен-ности";
            string s2 = "собственности";
            int result = Calculate(s1, s2);
            Assert.AreEqual(1, result);
        }

        [TestMethod]
        public void TryGetFieldTest()
        {
            string s1 = "N№ п/п";
            Assert.IsTrue(s1.IsNumber());
        }

        [TestMethod]
        public void HeaderDetectionTest()
        {
            string big_header = "Объекты недвижимости, находящиеся в собственности Вид\nсобствен\nности";
            DeclarationField field = HeaderHelpers.GetField(big_header);

            big_header = "Объекты недвижимости имущества находящиеся в пользовании Вид обьекта";
            field = HeaderHelpers.GetField(big_header);
        }
        
     
        [TestMethod]
        public void TestSwapCountryAndSquare()
        {
            string square = "рф";
            string country = "57 кв м";
            RealtyParser.SwapCountryAndSquare(ref square, ref country);
            Assert.AreEqual("рф", country);
            Assert.AreEqual("57 кв м", square);
            
            // no swap
            RealtyParser.SwapCountryAndSquare(ref square, ref country);
            Assert.AreEqual("57 кв м", square);
        }   
    }
}
