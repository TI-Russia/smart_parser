using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Lib;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace test
{
    [TestClass]
    public class TestApiPatterns
    {
        [TestMethod]
        public void TestPatterns()
        {
            string value = DeclaratorApiPatterns.ParseCountry("\"россия\"");
            Assert.AreEqual(value, "Россия");
            try
            {
                DeclaratorApiPatterns.ParseCountry("неправильная страна");
                Assert.Fail("no exception thrown");
            }
            catch (Exception ex)
            {
                Assert.IsTrue(ex is UnknownCountryException);
            }

            Assert.AreEqual(DeclaratorApiPatterns.GetValue("жилой дом(незавершенное строительство)", "realestatetype"), "Жилой дом");

            Assert.AreEqual(DeclaratorApiPatterns.GetValue("а/м супер пурер машина", "vehicletype"), "Автомобиль легковой");
        }
    }
}
