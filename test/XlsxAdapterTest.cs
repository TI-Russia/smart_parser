using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;
using System.IO;
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
            var columnOrdering = ColumnDetector.ExamineTableBeginning(adapter);
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);
            Declaration declaration = parser.Parse(columnOrdering, false, null);
            string comments = "";
            string output = DeclarationSerializer.Serialize(declaration, ref comments);
        }
        
    }
}
