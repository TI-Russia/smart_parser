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
            PatternsFileName.UseTestPatterns();
        }
        [TestMethod]
        public void TestParseSquare()
        {
            string square = "доля 1/1876 от 802898980";
            Decimal? result = DataHelper.ParseSquare(square);

            Assert.IsNull(result);
        }
        [TestMethod]
        public void TestParsePropertyAndOwnershipTypes()
        {
            string test6 = "квартира\n(совместная)";
            var tuple6 = DataHelper.ParseCombinedRealEstateColumn(test6);
            Assert.AreEqual(tuple6.Item1, RealEstateType.Apartment);
            Assert.AreEqual(tuple6.Item2, OwnershipType.Joint);
            Assert.AreEqual(tuple6.Item3, "");




            var square = DataHelper.ParseSquares("1/500")[0];
            Assert.AreEqual(square.Value.ToString(), "0,002");

                      
            string test4 = "долевая 1/249";
            OwnershipType ownershipType = DataHelper.TryParseOwnershipType(test4);
            Assert.AreEqual(ownershipType, OwnershipType.Shared);
            
        }

        [TestMethod]
        public void TestParsePropertyAndOwnershipTypes2()
        {
            string s = "(общая долевая собственность, 1/2)";
            OwnershipType ownershipType = DataHelper.TryParseOwnershipType(s);
            string share = DataHelper.ParseOwnershipShare(s, ownershipType);

            Assert.AreEqual(ownershipType, OwnershipType.Shared);
            Assert.AreEqual(share, "1/2");

            s = "(общая совместная собственность)";
            ownershipType = DataHelper.TryParseOwnershipType(s);
            Assert.AreEqual(ownershipType, OwnershipType.Joint);
        }

        [TestMethod]
        public void TestParsePropertyAndOwnershipTypes3()
        {
            string s = "квартира (наём на срок полномочий депутата ГД)";
            var result = DataHelper.ParseCombinedRealEstateColumn(s);
            Assert.IsTrue(result.Item1 == RealEstateType.Apartment);
            Assert.IsTrue(result.Item2 == OwnershipType.Lease);
                
            s = "квартира(безвозмездное пользование на срок полномочий депутата ГД)";
            result = DataHelper.ParseCombinedRealEstateColumn(s);
            Assert.IsTrue(result.Item1 == RealEstateType.Apartment);
            Assert.IsTrue(result.Item2 == OwnershipType.ServiceHousing);
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
        public void TestParseDocumentFileName()
        {
            string file1 = @"C:\Users\user\Dropbox\RawDeclarations\Ministries\min_agr_new\2013\9037\dep_gos_slyzhbi_2013.xls";
            string file2 = @"C:\Users\user\Dropbox\RawDeclarations\Ministries\min_agr_new\2014\30202.xls";

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

        }

    }
}
