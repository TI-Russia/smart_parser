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
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");

            //IAdapter adapter = XlsxParser.GetAdapter(xlsxFile);

            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);
            //Parser parser = new Parser(adapter);

            //parser.Process();
        }
    }
}
