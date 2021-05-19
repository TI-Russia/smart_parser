using System;
using System.Collections.Generic;
using System.Text;
using System.Drawing;
using System.Drawing.Text;

namespace TI.Declarator.ParserCommon
{
    public class TStringMeasure
    {
        static System.Drawing.Graphics DefaultGraphics;
        static public System.Drawing.Font DefaultFont = null;
        static float TestNormalizer;

        static bool IsLinux()
        {
            int p = (int)Environment.OSVersion.Platform;
            return (p == 4) || (p == 6) || (p == 128);
        }
        static public bool IsInitialized()
        {
            return DefaultFont != null;
        }
        static public void InitGraphics(string fontName, int fontSize)
        {
            if (IsLinux())
            {
                TestNormalizer = 1.07F;
            }
            else
            {
                TestNormalizer = 1.0F;
            }
            DefaultGraphics = System.Drawing.Graphics.FromImage(new Bitmap(1, 1));
            DefaultGraphics.TextRenderingHint = TextRenderingHint.SingleBitPerPixelGridFit;
            DefaultGraphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.None;
            DefaultGraphics.CompositingQuality = System.Drawing.Drawing2D.CompositingQuality.HighSpeed;
            DefaultGraphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Low;
            if (fontSize > 0)
            {
                DefaultFont = new System.Drawing.Font(fontName, fontSize / 2);
            }
            else
            {
                DefaultFont = null;
            }
            //DefaultFont = new System.Drawing.Font("Liberation Serif", fontSize / 2);
        }

        // This function (graphics.MeasureString in particular) can work differently on Unix and Windows, 
        // The difference is not caused by the default font on Linux  (Liberation Serif) and the default font on Windows(Times New Roman.
        // See the first column of sud_2016.doc from the test cases.  
        // https://stackoverflow.com/questions/8283631/graphics-drawstring-vs-textrenderer-drawtextwhich-can-deliver-better-quality
        public static float MeasureStringWidth(string s)
        {
            var stringSize = DefaultGraphics.MeasureString(s, DefaultFont);
            return stringSize.Width * TestNormalizer;
        }

        public static List<string> GetLinesWithSoftBreaks(string text, int cellWidth)
        {
            var res = new List<string>();
            if (text == null || text.Length == 0) return res;
            string[] hardLines = text.Split('\n');
            if (cellWidth == 0 || !TStringMeasure.IsInitialized())
            {
                return new List<string>(hardLines);
            }

            foreach (var hardLine in hardLines)
            {
                var width = TStringMeasure.MeasureStringWidth(hardLine);
                int defaultMargin = 11; //to do calc it really
                int softLinesCount = (int)(width / (cellWidth - defaultMargin)) + 1;
                if (softLinesCount == 1)
                {
                    res.Add(hardLine);
                }
                else
                {
                    int start = 0;
                    for (int k = 0; k < softLinesCount; ++k)
                    {
                        int len;
                        if (k + 1 == softLinesCount)
                        {
                            len = hardLine.Length - start;
                        }
                        else
                        {
                            len = (int)(hardLine.Length / softLinesCount);
                            int wordBreak = (start + len >= hardLine.Length) ? hardLine.Length : hardLine.LastIndexOf(' ', start + len);
                            if (wordBreak > start)
                            {
                                len = wordBreak - start;
                            }
                            else
                            {
                                wordBreak = hardLine.IndexOf(' ', start + 1);
                                len = (wordBreak == -1) ? hardLine.Length - start : wordBreak - start;
                            }
                        }
                        res.Add(hardLine.Substring(start, len));
                        start += len;
                        if (start >= hardLine.Length) break;
                    }
                }
            }
            // Logger.Info("result = {0}", string.Join("|\n", res));
            return res;
        }

    }
}
