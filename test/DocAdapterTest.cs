using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using System.IO;


namespace test
{
    [TestClass]
    public class DocAdapterTest
    {
        [TestMethod]
        public void AsposeDocAdapterTest()
        {
            string docFile = Path.Combine(TestUtil.GetTestDataPath(), "E - min_sport_2012_Rukovoditeli_gospredpriyatij,_podvedomstvennyih_ministerstvu.doc");
            //IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            IAdapter adapter = AsposeDocAdapter.CreateAdapter(docFile);

        }
    }
}
