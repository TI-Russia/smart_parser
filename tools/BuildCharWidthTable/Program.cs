using System;
using System.Collections.Generic;
using System.IO;
using TI.Declarator.ParserCommon;

namespace BuildCharWidthTable
{
    class Program
    {
        static int LatinStart = 32;
        static int LatinEnd = 128;

        static int CyrillicStart = 0x0410;
        static int CyrillicEnd = 0x0460;

        public static float GetMedian(float[] sourceNumbers)
        {
            //Framework 2.0 version of this method. there is an easier way in F4        
            if (sourceNumbers == null || sourceNumbers.Length == 0)
                throw new System.Exception("Median of empty array not defined.");

            //make sure the list is sorted, but use a new array
            float[] sortedPNumbers = (float[])sourceNumbers.Clone();
            Array.Sort(sortedPNumbers);

            //get the median
            int size = sortedPNumbers.Length;
            int mid = size / 2;
            float median = (size % 2 != 0) ? (float)sortedPNumbers[mid] : ((float)sortedPNumbers[mid] + (float)sortedPNumbers[mid - 1]) / 2;
            return median;
        }
        static void WriteCharPeriod(int start, int end, List<float> widths, StreamWriter outputFile)
        {
            outputFile.WriteLine("             //chars from {0} to {1}", start, end);
            outputFile.Write("             ");
            for (int i = start; i < end; ++i)
            {
                string ch = "";
                ch += (char)i;
                float width = TStringMeasure.MeasureStringWidth(ch, 1.0F);
                float afm_width = width * 1000.0f / TStringMeasure.FontSize; 
                widths.Add(afm_width);
                if (i != start)
                {
                    outputFile.Write(",");
                }
                outputFile.Write("{{ {0}, {1:0.00}F }}", i, afm_width);
            }

        }
        static public void BuildCharToWidth(string outfilePath, string mapName)
        {
            using (StreamWriter outputFile = new StreamWriter(outfilePath))
            {
                outputFile.WriteLine("        static Dictionary<int, float> {0} = new Dictionary<int, float> {{", mapName);
                List<float> widths = new List<float>();
                WriteCharPeriod(LatinStart, LatinEnd, widths, outputFile);
                outputFile.WriteLine(",");
                WriteCharPeriod(CyrillicStart, CyrillicEnd, widths, outputFile);
                outputFile.Write("\n        };\n");
                outputFile.WriteLine("        static float {0}_median = {1:0.00}F;", mapName, GetMedian(widths.ToArray()));

            }
        }

        static void Main(string[] args)
        {
            TStringMeasure.InitDefaultFont("Times New Roman", 10);
            BuildCharToWidth("time_new_roman_afm_char_width.txt", "TimesNewRomanAfmCharWidth");
        }
    }
}
