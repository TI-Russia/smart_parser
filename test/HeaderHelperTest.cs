using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using TI.Declarator.ExcelParser;
using System.IO;
using Smart.Parser.Lib;

namespace test
{
    [TestClass]
    public class HeaderHelperTest
    {
        [TestMethod]
        public void HeaderHelperTest1()
        {
            string docFile = Path.Combine(TestUtil.GetTestDataPath(), "E - min_sport_2012_Rukovoditeli_gospredpriyatij,_podvedomstvennyih_ministerstvu.doc");
            //IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            IAdapter adapter = AsposeDocAdapter.CreateAdapter(docFile);

        }
    }
}
