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

        public static int GetMedian(int[] sourceNumbers)
        {
            //Framework 2.0 version of this method. there is an easier way in F4        
            if (sourceNumbers == null || sourceNumbers.Length == 0)
                throw new System.Exception("Median of empty array not defined.");

            //make sure the list is sorted, but use a new array
            int[] sortedPNumbers = (int[])sourceNumbers.Clone();
            Array.Sort(sortedPNumbers);

            //get the median
            int size = sortedPNumbers.Length;
            int mid = size / 2;
            int median = (size % 2 != 0) ? (int)sortedPNumbers[mid] : ((int)sortedPNumbers[mid] + (int)sortedPNumbers[mid - 1]) / 2;
            return median;
        }
        static void WriteCharPeriod(int start, int end, List<int> widths, StreamWriter outputFile)
        {
            outputFile.WriteLine("             //chars from {0} to {1}", start, end);
            outputFile.Write("             ");
            for (int i = start; i < end; ++i)
            {
                string ch = "";
                ch += (char)i;
                float width = TStringMeasure.MeasureStringWidth(ch);
                int afm_width = (int)(width * 1000.0f / TStringMeasure.FontSize); 
                widths.Add(afm_width);
                if (i != start)
                {
                    outputFile.Write(",");
                }
                outputFile.Write("{{ {0}, {1} }}", i, afm_width);
            }

        }
        static public void BuildCharToWidth(string fontName, StreamWriter outputFile)
        {
            TStringMeasure.InitDefaultFontSystem(fontName, 10);
            string varName = fontName.Replace(' ', '_');
            outputFile.WriteLine("        static Dictionary<int, int> {0} = new Dictionary<int, int> {{", varName);
            List<int> widths = new List<int>();
            WriteCharPeriod(LatinStart, LatinEnd, widths, outputFile);
            outputFile.WriteLine(",");
            WriteCharPeriod(CyrillicStart, CyrillicEnd, widths, outputFile);
            outputFile.WriteLine(",\n             {{0, {0}}}", GetMedian(widths.ToArray()));
            outputFile.Write("        };\n");
        }

        static void Main(string[] args)
        {
            string[] fonts = { "Times New Roman", "Calibri", "Arial" };
            using (StreamWriter outputFile = new StreamWriter("CharMapWidths.cs"))
            {
                for (int i = 0; i < fonts.Length; ++i)
                {
                    BuildCharToWidth(fonts[i], outputFile);
                }
                
            }
        }
    }
}
