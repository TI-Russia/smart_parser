using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using Smart.Parser.Lib;

namespace test
{
    [TestClass]
    public class TestJsonWriter
    {
        [TestMethod]
        public void TestJson()
        {
            string jsonFile = Path.Combine(TestUtil.GetTestDataPath(), "example.json");
            RootObject data = JsonWriter.ReadJson(jsonFile);
            Assert.AreEqual(data.person.family_name, "Бродский");
        }
    }
}
