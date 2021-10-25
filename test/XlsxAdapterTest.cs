using StringHelpers;
using SmartParser.Lib;

using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using TI.Declarator.JsonSerialization;

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
            var columnOrdering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            SmartParser.Lib.Parser parser = new SmartParser.Lib.Parser(adapter);
            Declaration declaration = parser.Parse(columnOrdering, false, null);
            string comments = "";
            string output = DeclarationSerializer.Serialize(declaration, ref comments);
        }
        
    }
}
