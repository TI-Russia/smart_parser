using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Lib;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace test
{
    [TestClass]
    public class TestApiPatterns
    {
        [TestMethod]
        public void TestPatterns()
        {
            string value = DeclaratorApiPatterns.GetValue("\"россия\"", "country");
            Assert.IsTrue(value=="Russia");
            Assert.IsTrue(DeclaratorApiPatterns.GetValue("а/м супер пурер машина", "vehicletype") == "Автомобиль легковой");
            Assert.IsTrue(DeclaratorApiPatterns.GetValue("жилой дом(незавершенное строительство)", "realestatetype") == "Residential house");
        }
    }
}
