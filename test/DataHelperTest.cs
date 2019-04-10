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
        public void TestVechicle()
        {
            string vechicleString = "автомобили легковые: Toyota Camry, Mercedes Benz E 250";
            bool result = DataHelper.ParseVehicle(vechicleString, null);
            Assert.IsTrue(result);
            List<Vehicle> vechicles = new List<Vehicle>();
            result = DataHelper.ParseVehicle(vechicleString, vechicles);

            Assert.AreEqual(vechicles.Count, 2);
            Assert.AreEqual(vechicles[0].Text, "Toyota Camry");
            Assert.AreEqual(vechicles[1].Text, "Mercedes Benz E 250");
        }

        [TestMethod]
        public void TestParseArea()
        {
            string area = "доля 1/1876 от 802898980";
            Decimal? result = DataHelper.ParseArea(area);

            Assert.IsNull(result);
        }
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
            Assert.AreEqual(tuple3.Item1, RealEstateType.PlotOfLand);
            Assert.AreEqual(tuple3.Item2, OwnershipType.Shared);
            Assert.AreEqual(tuple3.Item3, "1/2");

            string test4 = "долевая 1/249";
            OwnershipType ownershipType = DataHelper.TryParseOwnershipType(test4);
            Assert.AreEqual(ownershipType, OwnershipType.Shared);
            share = DataHelper.ParseOwnershipShare(test4, ownershipType);

            string test5 = "жилой дом (незавершенное строительство)";
            var tuple5 = DataHelper.ParseCombinedRealEstateColumn(test5);
            Assert.AreEqual(tuple5.Item1, RealEstateType.ResidentialHouse);
            Assert.AreEqual(tuple5.Item2, OwnershipType.Ownership);
            Assert.AreEqual(tuple5.Item3, "");


            string test6 = "квартира\n(совместная)";
            var tuple6 = DataHelper.ParseCombinedRealEstateColumn(test6);
            Assert.AreEqual(tuple6.Item1, RealEstateType.Apartment);
            Assert.AreEqual(tuple6.Item2, OwnershipType.Joint);
            Assert.AreEqual(tuple6.Item3, "");

            string test7 = "Квартира долевая , 2/3";
            var tuple7 = DataHelper.ParseCombinedRealEstateColumn(test7);
            Assert.AreEqual(tuple7.Item1, RealEstateType.Apartment);
            Assert.AreEqual(tuple7.Item2, OwnershipType.Shared);
            Assert.AreEqual(tuple7.Item3, "2/3");
        }

        [TestMethod]
        public void TestParsePropertyAndOwnershipTypes2()
        {
            string test8 = "жилая блок-секция (общая долевая, 3/4)";
            var tuple8 = DataHelper.ParseCombinedRealEstateColumn(test8);
            Assert.AreEqual(tuple8.Item3, "3/4");

            string test9 = "квартира (общая долевая, 1/4)";
            var tuple9 = DataHelper.ParseCombinedRealEstateColumn(test9);
            Assert.AreEqual(tuple9.Item3, "1/4");
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
