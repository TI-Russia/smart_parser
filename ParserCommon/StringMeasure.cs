﻿using System;
using System.Collections.Generic;
using System.Text;
using System.Drawing;
using System.Drawing.Text;
using System.IO;
using SkiaSharp;

namespace StringHelpers
{
    public class TStringMeasure
    {
        static SKPaint DefaultPaint;
        static SKTypeface DefaultTypeface;

        static bool UseTimesNewRomanApproximated = false;

        static public int FontSize = 0;
        static public string FontName = "";
        static Dictionary<int, int> CurrentApproximatedTable = null;
        // generated by tools\BuildCharWidthTable
        static Dictionary<int, int> Times_New_Roman = new Dictionary<int, int> {
             //chars from 32 to 128
             { 32, 333 },{ 33, 222 },{ 34, 272 },{ 35, 333 },{ 36, 333 },{ 37, 555 },{ 38, 518 },{ 39, 120 },{ 40, 222 },{ 41, 222 },{ 42, 333 },{ 43, 375 },{ 44, 166 },{ 45, 222 },{ 46, 166 },{ 47, 185 },{ 48, 333 },{ 49, 333 },{ 50, 333 },{ 51, 333 },{ 52, 333 },{ 53, 333 },{ 54, 333 },{ 55, 333 },{ 56, 333 },{ 57, 333 },{ 58, 185 },{ 59, 185 },{ 60, 375 },{ 61, 375 },{ 62, 375 },{ 63, 295 },{ 64, 613 },{ 65, 481 },{ 66, 444 },{ 67, 444 },{ 68, 481 },{ 69, 407 },{ 70, 370 },{ 71, 481 },{ 72, 481 },{ 73, 222 },{ 74, 259 },{ 75, 481 },{ 76, 407 },{ 77, 592 },{ 78, 481 },{ 79, 481 },{ 80, 370 },{ 81, 481 },{ 82, 444 },{ 83, 370 },{ 84, 407 },{ 85, 481 },{ 86, 481 },{ 87, 629 },{ 88, 481 },{ 89, 481 },{ 90, 407 },{ 91, 222 },{ 92, 185 },{ 93, 222 },{ 94, 312 },{ 95, 333 },{ 96, 222 },{ 97, 295 },{ 98, 333 },{ 99, 295 },{ 100, 333 },{ 101, 295 },{ 102, 222 },{ 103, 333 },{ 104, 333 },{ 105, 185 },{ 106, 185 },{ 107, 333 },{ 108, 185 },{ 109, 518 },{ 110, 333 },{ 111, 333 },{ 112, 333 },{ 113, 333 },{ 114, 222 },{ 115, 259 },{ 116, 185 },{ 117, 333 },{ 118, 333 },{ 119, 481 },{ 120, 333 },{ 121, 333 },{ 122, 295 },{ 123, 319 },{ 124, 133 },{ 125, 319 },{ 126, 360 },{ 127, 366 },
             //chars from 1040 to 1120
             { 1040, 481 },{ 1041, 382 },{ 1042, 444 },{ 1043, 385 },{ 1044, 454 },{ 1045, 407 },{ 1046, 597 },{ 1047, 333 },{ 1048, 481 },{ 1049, 481 },{ 1050, 444 },{ 1051, 452 },{ 1052, 592 },{ 1053, 481 },{ 1054, 481 },{ 1055, 481 },{ 1056, 370 },{ 1057, 444 },{ 1058, 407 },{ 1059, 472 },{ 1060, 526 },{ 1061, 481 },{ 1062, 481 },{ 1063, 433 },{ 1064, 672 },{ 1065, 672 },{ 1066, 470 },{ 1067, 581 },{ 1068, 382 },{ 1069, 440 },{ 1070, 685 },{ 1071, 444 },{ 1072, 295 },{ 1073, 339 },{ 1074, 314 },{ 1075, 273 },{ 1076, 339 },{ 1077, 295 },{ 1078, 460 },{ 1079, 263 },{ 1080, 356 },{ 1081, 356 },{ 1082, 323 },{ 1083, 332 },{ 1084, 421 },{ 1085, 356 },{ 1086, 333 },{ 1087, 356 },{ 1088, 333 },{ 1089, 295 },{ 1090, 291 },{ 1091, 333 },{ 1092, 431 },{ 1093, 333 },{ 1094, 356 },{ 1095, 335 },{ 1096, 513 },{ 1097, 513 },{ 1098, 344 },{ 1099, 447 },{ 1100, 304 },{ 1101, 286 },{ 1102, 498 },{ 1103, 306 },{ 1104, 295 },{ 1105, 295 },{ 1106, 321 },{ 1107, 273 },{ 1108, 286 },{ 1109, 259 },{ 1110, 185 },{ 1111, 185 },{ 1112, 185 },{ 1113, 484 },{ 1114, 482 },{ 1115, 333 },{ 1116, 323 },{ 1117, 356 },{ 1118, 333 },{ 1119, 356 },
             {0, 333}
        };
        static Dictionary<int, int> Calibri = new Dictionary<int, int> {
             //chars from 32 to 128
             { 32, 332 },{ 33, 217 },{ 34, 267 },{ 35, 332 },{ 36, 337 },{ 37, 476 },{ 38, 454 },{ 39, 147 },{ 40, 202 },{ 41, 202 },{ 42, 332 },{ 43, 332 },{ 44, 166 },{ 45, 204 },{ 46, 168 },{ 47, 257 },{ 48, 337 },{ 49, 337 },{ 50, 337 },{ 51, 337 },{ 52, 337 },{ 53, 337 },{ 54, 337 },{ 55, 337 },{ 56, 337 },{ 57, 337 },{ 58, 178 },{ 59, 178 },{ 60, 332 },{ 61, 332 },{ 62, 332 },{ 63, 308 },{ 64, 596 },{ 65, 385 },{ 66, 362 },{ 67, 355 },{ 68, 410 },{ 69, 325 },{ 70, 306 },{ 71, 420 },{ 72, 415 },{ 73, 167 },{ 74, 212 },{ 75, 346 },{ 76, 280 },{ 77, 569 },{ 78, 430 },{ 79, 441 },{ 80, 344 },{ 81, 448 },{ 82, 361 },{ 83, 306 },{ 84, 324 },{ 85, 427 },{ 86, 378 },{ 87, 593 },{ 88, 346 },{ 89, 324 },{ 90, 312 },{ 91, 204 },{ 92, 257 },{ 93, 204 },{ 94, 332 },{ 95, 332 },{ 96, 194 },{ 97, 319 },{ 98, 350 },{ 99, 281 },{ 100, 350 },{ 101, 331 },{ 102, 203 },{ 103, 313 },{ 104, 350 },{ 105, 152 },{ 106, 159 },{ 107, 303 },{ 108, 152 },{ 109, 532 },{ 110, 350 },{ 111, 351 },{ 112, 350 },{ 113, 350 },{ 114, 232 },{ 115, 260 },{ 116, 223 },{ 117, 350 },{ 118, 301 },{ 119, 476 },{ 120, 288 },{ 121, 301 },{ 122, 263 },{ 123, 209 },{ 124, 306 },{ 125, 209 },{ 126, 332 },{ 127, 366 },
             //chars from 1040 to 1120
             { 1040, 385 },{ 1041, 358 },{ 1042, 362 },{ 1043, 286 },{ 1044, 429 },{ 1045, 325 },{ 1046, 533 },{ 1047, 315 },{ 1048, 427 },{ 1049, 427 },{ 1050, 361 },{ 1051, 407 },{ 1052, 569 },{ 1053, 415 },{ 1054, 441 },{ 1055, 414 },{ 1056, 344 },{ 1057, 355 },{ 1058, 324 },{ 1059, 351 },{ 1060, 464 },{ 1061, 346 },{ 1062, 425 },{ 1063, 370 },{ 1064, 578 },{ 1065, 593 },{ 1066, 409 },{ 1067, 507 },{ 1068, 354 },{ 1069, 365 },{ 1070, 585 },{ 1071, 370 },{ 1072, 319 },{ 1073, 355 },{ 1074, 319 },{ 1075, 230 },{ 1076, 372 },{ 1077, 331 },{ 1078, 459 },{ 1079, 281 },{ 1080, 360 },{ 1081, 360 },{ 1082, 309 },{ 1083, 340 },{ 1084, 450 },{ 1085, 356 },{ 1086, 351 },{ 1087, 347 },{ 1088, 350 },{ 1089, 281 },{ 1090, 258 },{ 1091, 301 },{ 1092, 416 },{ 1093, 288 },{ 1094, 361 },{ 1095, 312 },{ 1096, 485 },{ 1097, 499 },{ 1098, 357 },{ 1099, 444 },{ 1100, 313 },{ 1101, 295 },{ 1102, 481 },{ 1103, 316 },{ 1104, 331 },{ 1105, 331 },{ 1106, 360 },{ 1107, 230 },{ 1108, 295 },{ 1109, 260 },{ 1110, 152 },{ 1111, 152 },{ 1112, 159 },{ 1113, 500 },{ 1114, 513 },{ 1115, 355 },{ 1116, 309 },{ 1117, 360 },{ 1118, 301 },{ 1119, 349 },
             {0, 337}
        };
        static Dictionary<int, int> Arial = new Dictionary<int, int> {
             //chars from 32 to 128
             { 32, 370 },{ 33, 185 },{ 34, 236 },{ 35, 370 },{ 36, 370 },{ 37, 592 },{ 38, 444 },{ 39, 127 },{ 40, 222 },{ 41, 222 },{ 42, 259 },{ 43, 389 },{ 44, 185 },{ 45, 222 },{ 46, 185 },{ 47, 185 },{ 48, 370 },{ 49, 370 },{ 50, 370 },{ 51, 370 },{ 52, 370 },{ 53, 370 },{ 54, 370 },{ 55, 370 },{ 56, 370 },{ 57, 370 },{ 58, 185 },{ 59, 185 },{ 60, 389 },{ 61, 389 },{ 62, 389 },{ 63, 370 },{ 64, 676 },{ 65, 444 },{ 66, 444 },{ 67, 481 },{ 68, 481 },{ 69, 444 },{ 70, 407 },{ 71, 518 },{ 72, 481 },{ 73, 185 },{ 74, 333 },{ 75, 444 },{ 76, 370 },{ 77, 555 },{ 78, 481 },{ 79, 518 },{ 80, 444 },{ 81, 518 },{ 82, 481 },{ 83, 444 },{ 84, 407 },{ 85, 481 },{ 86, 444 },{ 87, 629 },{ 88, 444 },{ 89, 444 },{ 90, 407 },{ 91, 185 },{ 92, 185 },{ 93, 185 },{ 94, 312 },{ 95, 370 },{ 96, 222 },{ 97, 370 },{ 98, 370 },{ 99, 333 },{ 100, 370 },{ 101, 370 },{ 102, 185 },{ 103, 370 },{ 104, 370 },{ 105, 148 },{ 106, 148 },{ 107, 333 },{ 108, 148 },{ 109, 555 },{ 110, 370 },{ 111, 370 },{ 112, 370 },{ 113, 370 },{ 114, 222 },{ 115, 333 },{ 116, 185 },{ 117, 370 },{ 118, 333 },{ 119, 481 },{ 120, 333 },{ 121, 333 },{ 122, 333 },{ 123, 222 },{ 124, 173 },{ 125, 222 },{ 126, 389 },{ 127, 366 },
             //chars from 1040 to 1120
             { 1040, 444 },{ 1041, 437 },{ 1042, 444 },{ 1043, 361 },{ 1044, 451 },{ 1045, 444 },{ 1046, 615 },{ 1047, 402 },{ 1048, 479 },{ 1049, 479 },{ 1050, 388 },{ 1051, 437 },{ 1052, 555 },{ 1053, 481 },{ 1054, 518 },{ 1055, 479 },{ 1056, 444 },{ 1057, 481 },{ 1058, 407 },{ 1059, 423 },{ 1060, 506 },{ 1061, 444 },{ 1062, 493 },{ 1063, 444 },{ 1064, 611 },{ 1065, 624 },{ 1066, 527 },{ 1067, 590 },{ 1068, 437 },{ 1069, 479 },{ 1070, 673 },{ 1071, 481 },{ 1072, 370 },{ 1073, 381 },{ 1074, 354 },{ 1075, 243 },{ 1076, 388 },{ 1077, 370 },{ 1078, 445 },{ 1079, 305 },{ 1080, 372 },{ 1081, 372 },{ 1082, 291 },{ 1083, 388 },{ 1084, 458 },{ 1085, 368 },{ 1086, 370 },{ 1087, 361 },{ 1088, 370 },{ 1089, 333 },{ 1090, 305 },{ 1091, 333 },{ 1092, 548 },{ 1093, 333 },{ 1094, 381 },{ 1095, 347 },{ 1096, 534 },{ 1097, 548 },{ 1098, 416 },{ 1099, 479 },{ 1100, 347 },{ 1101, 340 },{ 1102, 499 },{ 1103, 361 },{ 1104, 370 },{ 1105, 370 },{ 1106, 370 },{ 1107, 243 },{ 1108, 340 },{ 1109, 333 },{ 1110, 148 },{ 1111, 185 },{ 1112, 148 },{ 1113, 604 },{ 1114, 541 },{ 1115, 370 },{ 1116, 291 },{ 1117, 372 },{ 1118, 333 },{ 1119, 368 },
             {0, 370}
        };

        static TStringMeasure()
        {
            // Initialize the SKPaint object
            DefaultPaint = new SKPaint
            {
                IsAntialias = true,
                SubpixelText = true,
                LcdRenderText = true,
                HintingLevel = SKPaintHinting.Full,
                FilterQuality = SKFilterQuality.High
            };
        }
        static public bool IsLinux()
        {
            int p = (int)Environment.OSVersion.Platform;
            return (p == 4) || (p == 6) || (p == 128);
        }
        static public bool IsInitialized()
        {
            return DefaultPaint != null || CurrentApproximatedTable != null;
        }

        static public void InitDefaultFontApproximated(string fontName, int fontSize)
        {
            if (fontName == "Arial")
            {
                CurrentApproximatedTable = Arial;
            }
            else if (fontName == "Calibri")
            {
                CurrentApproximatedTable = Calibri;
            }
            else
            {
                CurrentApproximatedTable = Times_New_Roman;
            }
            FontSize = fontSize;
        }
        static public void InitDefaultFontSystem(string fontName, int fontSizePoints)
        {
            CurrentApproximatedTable = null;
            FontName = fontName;
            FontSize = fontSizePoints; // Keep FontSize unchanged

            if (fontSizePoints > 0)
            {
                // Load the typeface
                DefaultTypeface = SKTypeface.FromFamilyName(fontName) ?? SKTypeface.Default;
                DefaultPaint.Typeface = DefaultTypeface;

                // Set TextSize to match fontSizePoints
                DefaultPaint.TextSize = fontSizePoints;
            }
            else
            {
                // Default font size
                DefaultTypeface = SKTypeface.Default;
                DefaultPaint.Typeface = DefaultTypeface;
                DefaultPaint.TextSize = 5f;
            }
            Console.WriteLine($"DefaultTypeface FamilyName: {DefaultTypeface.FamilyName}");
        }

        static public void InitDefaultFont(string fontName, int fontSize)
        {
            //InitDefaultFontSystem(fontName, fontSize);
            InitDefaultFontApproximated(fontName, fontSize);
        }

        static float StringWidthApproximated(Dictionary<int, int> mapToWidth, string s)
        {
            float width = 0;
            int defaultValue = mapToWidth[0];
            foreach (var c in s)
            {
                int w = defaultValue;
                mapToWidth.TryGetValue((int)c, out w);
                width += (float)(w * FontSize) / 1000.0F;
            }
            return width;
        }

        // This function (graphics.MeasureString in particular) can work differently on Unix and Windows, 
        // The difference is not caused by the default font on Linux  (Liberation Serif) and the default font on Windows(Times New Roman.
        // See the first column of sud_2016.doc from the test cases.  
        // https://stackoverflow.com/questions/8283631/graphics-drawstring-vs-textrenderer-drawtextwhich-can-deliver-better-quality
        public static float MeasureStringWidth(string s)
        {
            s = s.Replace(' ', '_');

            if (CurrentApproximatedTable != null)
            {
                return StringWidthApproximated(CurrentApproximatedTable, s);
            }

            if (DefaultPaint == null)
            {
                throw new InvalidOperationException("DefaultPaint is not initialized. Call InitDefaultFont first.");
            }

            // Measure text width using SkiaSharp
            float width = DefaultPaint.MeasureText(s);

            return width;
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
