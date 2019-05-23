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
            string test6 = "квартира\n(совместная)";
            var tuple6 = DataHelper.ParseCombinedRealEstateColumn(test6);
            Assert.AreEqual(tuple6.Item1, RealEstateType.Apartment);
            Assert.AreEqual(tuple6.Item2, OwnershipType.Joint);
            Assert.AreEqual(tuple6.Item3, "");




            string test3 = "земельный участок ИЖС                             (общая, долевая, 1/2 доли)";
            var tuple3 = DataHelper.ParseCombinedRealEstateColumn(test3);
            Assert.AreEqual(tuple3.Item1, RealEstateType.PlotOfLand);
            Assert.AreEqual(tuple3.Item2, OwnershipType.Shared);
            Assert.AreEqual(tuple3.Item3, "1/2");

            //var result2 = DataHelper.ParsePropertyAndOwnershipTypes("земельный участок\n(общая, долевая, 1/2 доли)");
            //Assert.AreEqual(result2[0].Item1, RealEstateType.PlotOfLand);
            ////Assert.AreEqual(result2[0].Item2, OwnershipType.Joint);
            //Assert.AreEqual(result2[0].Item3, "1/2");
            //
            //List<Tuple<RealEstateType, OwnershipType, string>> result =
            //    DataHelper.ParsePropertyAndOwnershipTypes("квартира    (совместная)");
            //
            //Assert.AreEqual(result[0].Item1, RealEstateType.Apartment);
            //Assert.AreEqual(result[0].Item2, OwnershipType.Joint);


            string share;
            //var ownType = DataHelper.ParseOwnershipTypeAndShare("долевая, 1/4", out share);
            //Assert.AreEqual(ownType, OwnershipType.Shared);
            //Assert.AreEqual(share, "1/4");


            var area = DataHelper.ParseAreas("1/500")[0];
            Assert.AreEqual(area.Value.ToString(), "0,002");

            string test1 = "квартира           (безвозмездное, бессрочное пользование)";
            string test2 = "Квартира долевая , 2/3";

            var tuple1 = DataHelper.ParseCombinedRealEstateColumn(test1);
            var tuple2 = DataHelper.ParseCombinedRealEstateColumn(test2);




            string test4 = "долевая 1/249";
            OwnershipType ownershipType = DataHelper.TryParseOwnershipType(test4);
            Assert.AreEqual(ownershipType, OwnershipType.Shared);
            share = DataHelper.ParseOwnershipShare(test4, ownershipType);

            string test5 = "жилой дом (незавершенное строительство)";
            var tuple5 = DataHelper.ParseCombinedRealEstateColumn(test5);
            Assert.AreEqual(tuple5.Item1, RealEstateType.ResidentialHouse);
            Assert.AreEqual(tuple5.Item2, OwnershipType.Ownership);
            Assert.AreEqual(tuple5.Item3, "");


            string test7 = "Квартира долевая , 2/3";
            var tuple7 = DataHelper.ParseCombinedRealEstateColumn(test7);
            Assert.AreEqual(tuple7.Item1, RealEstateType.Apartment);
            Assert.AreEqual(tuple7.Item2, OwnershipType.Shared);
            Assert.AreEqual(tuple7.Item3, "2/3");

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
        public void TestParseVehicle()
        {
            string vechicleString = "-";
            List<Vehicle> vechicles = new List<Vehicle>();

            bool result = DataHelper.ParseVehicle(vechicleString, vechicles);
            Assert.IsFalse(result);

            vechicleString = "автомобили легковые: ЛЭНД РОВЕР Discovery Sport мототранспортные средства: мотовездеход KOMANDER LTD, снегоход Bombardier SKI-DOO expedition TUV V-1000, снегоход SKI-DOO SKANDIC SWT 900 ACE водный транспорт: катер SKY-BOAT-500R иные транспортные средства: прицеп МЗСА 817717";
            result = DataHelper.ParseVehicle(vechicleString, vechicles);
            Assert.IsTrue(result);
            Assert.AreEqual(vechicles.Count, 6);
        }
        [TestMethod]
        public void TestParseVehicle2()
        {
            string vechicleString = "Автомобиль легковой\nHyundai Tucson";
            List<Vehicle> vechicles = new List<Vehicle>();

            bool result = DataHelper.ParseVehicle(vechicleString, vechicles);
            Assert.IsTrue(result);
            Assert.AreEqual(vechicles.Count, 1);
            Assert.AreEqual(vechicles[0].Text, "Hyundai Tucson");
            Assert.AreEqual(vechicles[0].Type, "Автомобиль легковой");

            vechicleString = "Автомобиль легковой Jeep Compass";
            result = DataHelper.ParseVehicle(vechicleString, vechicles);
            Assert.IsTrue(result);
            Assert.AreEqual(vechicles.Count, 1);
            Assert.AreEqual("Jeep Compass", vechicles[0].Text);
            Assert.AreEqual("Автомобиль легковой", vechicles[0].Type);


        }

    }
}
