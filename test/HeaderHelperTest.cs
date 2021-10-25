using StringHelpers;
using SmartParser.Lib;

using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using System;

namespace test
{
    [TestClass]
    public class HeaderHelperTest
    {
        
        [TestMethod]
        public void StringComparisonTest()
        {
            string s1 = "собствен-ности";
            string s2 = "собственности";
            int result = LevenshteinDistance.Calculate(s1, s2);
            Assert.AreEqual(1, result);
        }

        [TestMethod]
        public void TryGetFieldTest()
        {
            string s1 = "N№ п/п";
            Assert.IsTrue(s1.IsNumber());
        }

        public static DeclarationField GetField(string str)
        {
            var f = HeaderHelpers.TryGetField("", str);
            if (f == DeclarationField.None)
            {
                throw new Exception($"Could not determine column type for header {str}.");
            }
            return f;
        }


        [TestMethod]
        public void HeaderDetectionTest()
        {
            string big_header = "Объекты недвижимости, находящиеся в собственности Вид\nсобствен\nности";
            DeclarationField field = GetField(big_header);

            big_header = "Объекты недвижимости имущества находящиеся в пользовании Вид обьекта";
            field = GetField(big_header);
        }
        
     
        [TestMethod]
        public void TestSwapCountryAndSquare()
        {
            string square = "рф";
            string country = "57 кв м";
            Assert.IsTrue(TRealtyCellSpan.CountryAndSquareAreSwapped(square, country));
            Assert.IsFalse(TRealtyCellSpan.CountryAndSquareAreSwapped(country, square));
        }

        [TestMethod]
        public void TestCanBePersonName()
        {
            string s = "Десятов Владимир  Вячеславович,";
            ColumnByDataPredictor.InitializeIfNotAlready();
            var r = DataRow.CheckPersonName(s);
            Assert.IsTrue(r);
        }
    }
}

