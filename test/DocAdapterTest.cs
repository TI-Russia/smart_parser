using System.Drawing;
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
            IAdapter adapter = AsposeDocAdapter.CreateAdapter(docFile);

        }
        
        [TestMethod]
        public void FontWidthTest()
        {
            var graphics = System.Drawing.Graphics.FromImage(new Bitmap(1, 1));
            var FontName = "Times New Roman";
            var testLine = "Test width of long string - whats that?";
            var FontSize = 10;
            var font = new System.Drawing.Font(FontName, FontSize / 2);
            var stringSize = graphics.MeasureString(testLine, font);
            Assert.AreEqual(103, stringSize.Width);
            Assert.AreEqual(8, stringSize.Height);
        }
        
    }
}
