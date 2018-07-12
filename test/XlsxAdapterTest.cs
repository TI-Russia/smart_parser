using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;
using System.IO;
using TI.Declarator.ExcelParser;

namespace test
{
    [TestClass]
    public class XlsxAdapterTest
    {
        [TestMethod]
        public void XlsxTypeCTest()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "c_sample.xlsx");

            IAdapter adapter = XlsxParser.GetAdapter("Test.xlsx");

            //IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            //Parser parser = new Parser(adapter);

            //parser.Process();
        }
    }
}
