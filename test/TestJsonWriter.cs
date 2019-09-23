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
        public void TestColumnOrderJson()
        {
            ColumnOrdering co = new ColumnOrdering();
            TColumnInfo s = new TColumnInfo();
            s.Field = DeclarationField.NameOrRelativeType;
            co.Add(s);
            JsonWriter.WriteJson("co.json", co);
        }
    }
}
