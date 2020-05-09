using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Text;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using System.IO;
using Aspose.Words.Fields;

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
            SizeF RunGraphicMeasure(string s, string fileName, TextRenderingHint textHint)
            {
                var myBitmap = new Bitmap(350, 30);
                var graphics = System.Drawing.Graphics.FromImage(myBitmap);
                var FontName = "Times New Roman";
                var FontSize = 20;
                var drawBrush = new SolidBrush(Color.White);
                var font = new System.Drawing.Font(
                    FontName,
                    FontSize,
                    FontStyle.Regular,
                    GraphicsUnit.Pixel);

                graphics.TextRenderingHint = textHint;
                graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.None;
                graphics.CompositingQuality = System.Drawing.Drawing2D.CompositingQuality.HighSpeed;
                graphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Low;
                graphics.DrawString(s, font, drawBrush, 0, 0);

                var myImageCodecInfo = GetEncoderInfo("image/jpeg");
                var myEncoder = Encoder.Quality;
                var myEncoderParameter = new EncoderParameter(myEncoder, 100L);
                var myEncoderParameters = new EncoderParameters(1);
                myEncoderParameters.Param[0] = myEncoderParameter;
                myBitmap.Save(fileName, myImageCodecInfo, myEncoderParameters);
                var sizeF = graphics.MeasureString(s, font);
                return sizeF;
            }

            var testLine = "Test width of long string - whats that?";
            var stringSize = RunGraphicMeasure(testLine,"test-string-SingleBitPerPixel.jpg", TextRenderingHint.SingleBitPerPixelGridFit );
            Assert.AreEqual(298, stringSize.Width);
            // Assert.AreEqual(23, stringSize.Height);

            // stringSize = RunGraphicMeasure(testLine,"test-string-SingleBitPerPixelGridFit.jpg", TextRenderingHint.SingleBitPerPixelGridFit );
            // stringSize = RunGraphicMeasure(testLine,"test-string-SystemDefault.jpg", TextRenderingHint.SystemDefault );
            // stringSize = RunGraphicMeasure(testLine,"test-string-ClearTypeGridFit.jpg", TextRenderingHint.ClearTypeGridFit );
            // stringSize = RunGraphicMeasure(testLine,"test-string-AntiAliasGridFit.jpg", TextRenderingHint.AntiAliasGridFit );
            // stringSize = RunGraphicMeasure(testLine,"test-string-AntiAlias.jpg", TextRenderingHint.AntiAlias );
            
        }
        
    }
}
