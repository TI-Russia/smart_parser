using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;
using System.IO;
using TI.Declarator.ExcelParser;
using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;

namespace test
{
    [TestClass]
    public class XlsxAdapterTest
    {
        [TestMethod]
        public void XlsxTypeCTest()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "c_sample.xlsx");


            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);

            var columnOrdering = ColumnDetector.ExamineHeader(adapter);
            adapter.ColumnOrdering = columnOrdering;


            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);

            Declaration declaration = parser.Parse();

            string output = DeclarationSerializer.Serialize(declaration, true);


            //parser.Process();
        }
        [TestMethod]
        public void XlsxTest2()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract2.xlsx");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);

            var columnOrdering = ColumnDetector.ExamineHeader(adapter);
            adapter.ColumnOrdering = columnOrdering;
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);
            Declaration declaration = parser.Parse();

            string output = DeclarationSerializer.Serialize(declaration, true);
        }
    }
}
