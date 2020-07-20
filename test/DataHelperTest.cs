using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using System.IO;
using Smart.Parser.Lib;
using System.Collections.Generic;

namespace test
{
    [TestClass]
    public class DataHelperTest
    {
        public DataHelperTest()
        {
        }
        [TestMethod]
        public void TestParseSquare()
        {
            string square = "доля 1/1876 от 802898980";
            Decimal? result = DataHelper.ParseSquare(square);

            Assert.IsNull(result);
        }
        [TestMethod]
        public void TestParseNames()
        {
            var result = DataHelper.IsPublicServantInfo(" Санжицыренова Н.Ж.-Д.");
            Assert.IsTrue(result);
            result = DataHelper.IsPublicServantInfo("Блохин В.");
            Assert.IsTrue(result);

            result = DataHelper.IsPublicServantInfo("Ибрагимов С.-Э.С.-А.");
            Assert.IsTrue(result);

            result = DataHelper.IsPublicServantInfo("ВИЛИСОВА ГАЛИНА ИВАНОВНА");
            Assert.IsTrue(result);
        }

        [TestMethod]
        public void TestPublicServantInfo()
        {
            bool result = DataHelper.IsPublicServantInfo("ребенок");
            Assert.IsFalse(result);
        }

        [TestMethod]
        public void TestCountriesRegexp()
        {
            string s = "Италия";
            var countries = DataHelper.ParseCountryList(s);
            Assert.IsTrue(countries.Count == 1 );
            Assert.IsTrue(countries[0] == "Италия");

            s = "Саудовская Аравия  Российская Федерация";
            countries = DataHelper.ParseCountryList(s);
            Assert.IsTrue(countries.Count == 2);
            Assert.IsTrue(countries[0] == "Саудовская Аравия");
            Assert.IsTrue(countries[1] == "Российская Федерация");

        }

        [TestMethod]
        public void TestReadSquareAndCountry()
        {
            string s = "1 Россия";
            decimal square;
            string country;
            var r = DataHelper.ReadSquareAndCountry(s, out square, out country);
            Assert.IsTrue(square == 1);
            Assert.IsTrue(country == "Россия");
            
            s = "(Россия)";
            r = DataHelper.ReadSquareAndCountry(s, out square, out country);
            Assert.IsFalse(r);
        }

        [TestMethod]
        public void TestParseDocumentFileName()
        {
            string file1 = @"min_agr_new/2013/9037/dep_gos_slyzhbi_2013.xls";
            string file2 = @"Ministries/min_agr_new/2014/30202.xls";
            string file3 = @"Test Samples/2577/6.docx";

            int? id;
            string archive_file;

            bool result = DataHelper.ParseDocumentFileName(file1, out id, out archive_file);
            Assert.IsTrue(result);
            Assert.AreEqual(9037, id.Value);
            Assert.AreEqual("dep_gos_slyzhbi_2013.xls", archive_file);

            result = DataHelper.ParseDocumentFileName(file2, out id, out archive_file);
            Assert.IsTrue(result);
            Assert.AreEqual(30202, id.Value);
            Assert.AreEqual(null, archive_file);

            result = DataHelper.ParseDocumentFileName(file3, out id, out archive_file);
            Assert.IsTrue(result);
            Assert.AreEqual(2577, id.Value);
            Assert.AreEqual("6.docx", archive_file);
        }

    }
}
