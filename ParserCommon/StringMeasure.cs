using System;
using System.Collections.Generic;
using System.Text;
using System.Drawing;
using System.Drawing.Text;
using System.IO;

namespace TI.Declarator.ParserCommon
{
    public class TStringMeasure
    {

        static Dictionary<int, float> TimesNewRomanAfmCharWidth = new Dictionary<int, float> {
             //chars from 32 to 128
             { 32, 333.33F },{ 33, 222.01F },{ 34, 272.14F },{ 35, 333.33F },{ 36, 333.33F },{ 37, 555.34F },{ 38, 518.55F },{ 39, 120.12F },{ 40, 222.01F },{ 41, 222.01F },{ 42, 333.33F },{ 43, 375.98F },{ 44, 166.67F },{ 45, 222.01F },{ 46, 166.67F },{ 47, 185.22F },{ 48, 333.33F },{ 49, 333.33F },{ 50, 333.33F },{ 51, 333.33F },{ 52, 333.33F },{ 53, 333.33F },{ 54, 333.33F },{ 55, 333.33F },{ 56, 333.33F },{ 57, 333.33F },{ 58, 185.22F },{ 59, 185.22F },{ 60, 375.98F },{ 61, 375.98F },{ 62, 375.98F },{ 63, 295.90F },{ 64, 613.93F },{ 65, 481.45F },{ 66, 444.66F },{ 67, 444.66F },{ 68, 481.45F },{ 69, 407.23F },{ 70, 370.77F },{ 71, 481.45F },{ 72, 481.45F },{ 73, 222.01F },{ 74, 259.44F },{ 75, 481.45F },{ 76, 407.23F },{ 77, 592.77F },{ 78, 481.45F },{ 79, 481.45F },{ 80, 370.77F },{ 81, 481.45F },{ 82, 444.66F },{ 83, 370.77F },{ 84, 407.23F },{ 85, 481.45F },{ 86, 481.45F },{ 87, 629.23F },{ 88, 481.45F },{ 89, 481.45F },{ 90, 407.23F },{ 91, 222.01F },{ 92, 185.22F },{ 93, 222.01F },{ 94, 312.83F },{ 95, 333.33F },{ 96, 222.01F },{ 97, 295.90F },{ 98, 333.33F },{ 99, 295.90F },{ 100, 333.33F },{ 101, 295.90F },{ 102, 222.01F },{ 103, 333.33F },{ 104, 333.33F },{ 105, 185.22F },{ 106, 185.22F },{ 107, 333.33F },{ 108, 185.22F },{ 109, 518.55F },{ 110, 333.33F },{ 111, 333.33F },{ 112, 333.33F },{ 113, 333.33F },{ 114, 222.01F },{ 115, 259.44F },{ 116, 185.22F },{ 117, 333.33F },{ 118, 333.33F },{ 119, 481.45F },{ 120, 333.33F },{ 121, 333.33F },{ 122, 295.90F },{ 123, 319.99F },{ 124, 133.46F },{ 125, 319.99F },{ 126, 360.68F },{ 127, 366.54F },
             //chars from 1040 to 1120
             { 1040, 481.45F },{ 1041, 382.81F },{ 1042, 444.66F },{ 1043, 385.42F },{ 1044, 454.75F },{ 1045, 407.23F },{ 1046, 597.33F },{ 1047, 333.98F },{ 1048, 481.45F },{ 1049, 481.45F },{ 1050, 444.66F },{ 1051, 452.15F },{ 1052, 592.77F },{ 1053, 481.45F },{ 1054, 481.45F },{ 1055, 481.45F },{ 1056, 370.77F },{ 1057, 444.66F },{ 1058, 407.23F },{ 1059, 472.01F },{ 1060, 526.69F },{ 1061, 481.45F },{ 1062, 481.45F },{ 1063, 433.27F },{ 1064, 672.53F },{ 1065, 672.53F },{ 1066, 470.70F },{ 1067, 581.38F },{ 1068, 382.81F },{ 1069, 440.10F },{ 1070, 685.22F },{ 1071, 444.66F },{ 1072, 295.90F },{ 1073, 339.19F },{ 1074, 314.78F },{ 1075, 273.44F },{ 1076, 339.19F },{ 1077, 295.90F },{ 1078, 460.61F },{ 1079, 263.35F },{ 1080, 356.77F },{ 1081, 356.77F },{ 1082, 323.89F },{ 1083, 332.68F },{ 1084, 421.87F },{ 1085, 356.77F },{ 1086, 333.33F },{ 1087, 356.77F },{ 1088, 333.33F },{ 1089, 295.90F },{ 1090, 291.34F },{ 1091, 333.33F },{ 1092, 431.97F },{ 1093, 333.33F },{ 1094, 356.77F },{ 1095, 335.29F },{ 1096, 513.35F },{ 1097, 513.35F },{ 1098, 344.73F },{ 1099, 447.92F },{ 1100, 304.04F },{ 1101, 286.13F },{ 1102, 498.05F },{ 1103, 306.64F },{ 1104, 295.90F },{ 1105, 295.90F },{ 1106, 321.94F },{ 1107, 273.44F },{ 1108, 286.13F },{ 1109, 259.44F },{ 1110, 185.22F },{ 1111, 185.22F },{ 1112, 185.22F },{ 1113, 484.70F },{ 1114, 482.10F },{ 1115, 333.33F },{ 1116, 323.89F },{ 1117, 356.77F },{ 1118, 333.33F },{ 1119, 356.77F }
        };
        static float TimesNewRomanAfmCharWidth_median = 333.33F;

        static System.Drawing.Graphics DefaultGraphics;
        static public System.Drawing.Font DefaultFont = null;
        static float TestNormalizer;
        static bool UseTimesNewRomanApproximated = false;
        static public int FontSize = 0;
        static public string FontName = "";
        

        static TStringMeasure()
        {
            if (IsLinux())
            {
                //TestNormalizer = 1.07F;
                TestNormalizer = 1.19F;
            }
            else
            {
                TestNormalizer = 1.0F;
            }
            DefaultGraphics = System.Drawing.Graphics.FromImage(new Bitmap(1, 1));
            DefaultGraphics.TextRenderingHint = TextRenderingHint.AntiAlias;
            DefaultGraphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.None;
            DefaultGraphics.CompositingQuality = System.Drawing.Drawing2D.CompositingQuality.HighSpeed;
            DefaultGraphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.Low;
        }
        static public bool IsLinux()
        {
            int p = (int)Environment.OSVersion.Platform;
            return (p == 4) || (p == 6) || (p == 128);
        }
        static public bool IsInitialized()
        {
            return DefaultFont != null;
        }
        static public void InitDefaultFontApproximated(int fontSize)
        {
            UseTimesNewRomanApproximated = true;
            FontSize = fontSize;
        }
        static public void InitDefaultFont(string fontName, int fontSize)
        {
            UseTimesNewRomanApproximated = false;
            FontSize = fontSize;
            FontName = fontName;
            if (fontSize > 0)
            {
                DefaultFont = new System.Drawing.Font(fontName, fontSize / 2);
            }
            else
            {
                DefaultFont = new System.Drawing.Font("Times New Roman", 5);
            }
        }

        static float StringWidthApproximated(Dictionary<int, float> mapToWidth, float defaultValue, string s)
        {
            float width = 0;
            foreach (var c in s)
            {
                float w = defaultValue;
                mapToWidth.TryGetValue((int)c, out w);
                width += w * (float)FontSize / 1000.0F;
            }
            return width;
        }

        // This function (graphics.MeasureString in particular) can work differently on Unix and Windows, 
        // The difference is not caused by the default font on Linux  (Liberation Serif) and the default font on Windows(Times New Roman.
        // See the first column of sud_2016.doc from the test cases.  
        // https://stackoverflow.com/questions/8283631/graphics-drawstring-vs-textrenderer-drawtextwhich-can-deliver-better-quality
        public static float MeasureStringWidth(string s, float normalizer = 0.0F)
        {
            s = s.Replace(' ', '_');
            if (UseTimesNewRomanApproximated)
            {
                return StringWidthApproximated(TimesNewRomanAfmCharWidth, TimesNewRomanAfmCharWidth_median, s);
            }
            //var stringSize = DefaultGraphics.MeasureString(s, DefaultFont);
            var stringSize = DefaultGraphics.MeasureString(s, DefaultFont, 10000, StringFormat.GenericTypographic);

            if (normalizer != 0.0F)
            {
                return stringSize.Width * normalizer;
            }
            else
            {
                return stringSize.Width * TestNormalizer;
            }
        }

        public static List<string> GetLinesBySoftBreaks(string text, int cellWidth)
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
