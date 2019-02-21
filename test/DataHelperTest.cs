using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using TI.Declarator.ExcelParser;
using System.IO;
using Smart.Parser.Lib;
using System.Collections.Generic;

namespace test
{
    [TestClass]
    public class DataHelperTest
    {
        [TestMethod]
        public void TestParsePropertyAndOwnershipTypes()
        {
            var result2 = DataHelper.ParsePropertyAndOwnershipTypes("земельный участок\n(общая, долевая, 1/2 доли)");
            Assert.AreEqual(result2[0].Item1, RealEstateType.PlotOfLand);
            //Assert.AreEqual(result2[0].Item2, OwnershipType.Joint);
            Assert.AreEqual(result2[0].Item3, "1/2");

            List<Tuple<RealEstateType, OwnershipType, string>> result =
                DataHelper.ParsePropertyAndOwnershipTypes("квартира    (совместная)");

            Assert.AreEqual(result[0].Item1, RealEstateType.Apartment);
            Assert.AreEqual(result[0].Item2, OwnershipType.Joint);


            string share;
            var ownType = DataHelper.ParseOwnershipTypeAndShare("долевая, 1/4", out share);
            Assert.AreEqual(ownType, OwnershipType.Shared);
            Assert.AreEqual(share, "1/4");


            var area = DataHelper.ParseAreas("1/500")[0];
            Assert.AreEqual(area.Value.ToString(), "0,002");

            string test1 = "квартира           (безвозмездное, бессрочное пользование)";
            string test2 = "Квартира долевая , 2/3";

            var tuple1 = DataHelper.ParseCombinedRealEstateColumn(test1);
            var tuple2 = DataHelper.ParseCombinedRealEstateColumn(test2);



            string test3 = "земельный участок ИЖС                             (общая, долевая, 1/2 доли)";
            var tuple3 = DataHelper.ParseCombinedRealEstateColumn(test3);
            string test4 = "долевая 1/249";
            OwnershipType ownershipType = DataHelper.TryParseOwnershipType(test4);
            Assert.AreEqual(ownershipType, OwnershipType.Shared);
            share = DataHelper.ParseOwnershipShare(test4, ownershipType);

        }

        [TestMethod]
        public void TestParseNames()
        {
            var result = DataHelper.IsPublicServantInfo(" Санжицыренова Н.Ж.-Д.");
            Assert.IsTrue(result);
            result = DataHelper.IsPublicServantInfo("Блохин В.");
            Assert.IsTrue(result);
        }
    }
}
