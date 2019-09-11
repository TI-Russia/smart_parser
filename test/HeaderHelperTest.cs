using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using System.IO;
using Smart.Parser.Lib;
using static Algorithms.LevenshteinDistance;

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
        [TestMethod]
        public void StringComparisonTest()
        {
            string s1 = "собствен-ности";
            string s2 = "собственности";
            int result = Calculate(s1, s2);
            Assert.AreEqual(1, result);
        }

        [TestMethod]
        public void LineBreakFieldDetectionTest()
        {
            string big_header = "Объекты недвижимости, находящиеся в собственности Вид\nсобствен\nности";
            DeclarationField field = HeaderHelpers.GetField(big_header);

        }

    }
}
