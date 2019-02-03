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
            

        }
    }
}
