using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using Smart.Parser.Lib;
using TI.Declarator.ParserCommon;


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
        [TestMethod]
        public void TestColumnOrderJson()
        {
            ColumnOrdering co = new ColumnOrdering();

            co.Add(DeclarationField.NameOrRelativeType, 1);

            JsonWriter.WriteJson("co.json", co);


        }
    }
}
