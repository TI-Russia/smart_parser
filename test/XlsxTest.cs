using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Lib;
using Smart.Parser.Adapters;

namespace test
{
    [TestClass]
    public class XlsxTest
    {
        [TestMethod]
        public void XlsxTypeCTest()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");
            IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            Parser parser = new Parser(adapter);

            parser.Process();
        }
    }
}
