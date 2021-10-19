using SmartParser.Lib;

using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace test
{
    [TestClass]
    public class XlsxTest
    {
        [TestMethod]
        public void XlsxTypeCTest()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);
        }
    }
}
