using System;
using System.Drawing;
using System.Drawing.Imaging;
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
            var fileName = "E - min_sport_2012_Rukovoditeli_gospredpriyatij,_podvedomstvennyih_ministerstvu.doc";
            string docFile = Path.Combine(TestUtil.GetTestDataPath(), fileName);
            IAdapter adapter = AsposeDocAdapter.CreateAdapter(docFile);

        }

        private static ImageCodecInfo GetEncoderInfo(String mimeType)
        {
            int j;
            ImageCodecInfo[] encoders;
            encoders = ImageCodecInfo.GetImageEncoders();
            for(j = 0; j < encoders.Length; ++j)
            {
                if(encoders[j].MimeType == mimeType)
                    return encoders[j];
            }
            return null;
        }            

        [TestMethod]
        public void FontWidthTest()
        {
            var testLine = "Test width of long string - whats that?";

            var myBitmap = new Bitmap(250, 20);
            var graphics = System.Drawing.Graphics.FromImage(myBitmap);
            var FontName = "Times New Roman";
            var FontSize = 10;
            var fontTest = new System.Drawing.Font(
                FontName,
                FontSize);

            var font = new System.Drawing.Font(
                FontName,
                FontSize,
                FontStyle.Regular,
                GraphicsUnit.Point);

            SolidBrush drawBrush = new SolidBrush(Color.White);
            graphics.DrawString(testLine, font, drawBrush, 0, 0);
            
            var myImageCodecInfo = GetEncoderInfo("image/jpeg");
            var myEncoder = Encoder.Quality;
            var myEncoderParameter = new EncoderParameter(myEncoder, 100L);
            var myEncoderParameters = new EncoderParameters(1);
            myEncoderParameters.Param[0] = myEncoderParameter;

            myBitmap.Save("test-string.jpg", myImageCodecInfo, myEncoderParameters);
            
            var stringSize = graphics.MeasureString(testLine, font);
            Assert.AreEqual(103 * 2, stringSize.Width);
            Assert.AreEqual(15, stringSize.Height);
        }
        
    }
}
