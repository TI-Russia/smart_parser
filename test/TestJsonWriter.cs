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

            co.Add(DeclarationField.NameOrRelativeType, 1);

            JsonWriter.WriteJson("co.json", co);


        }
    }
}
