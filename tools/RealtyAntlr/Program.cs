using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace SmartAntlr
{

    class Program
    {
        // separated by an empty line
        static List<string> ReadTestCases(string inputPath)
        {
            var lines = new List<string>();
            foreach (string line in File.ReadLines(inputPath))
            {
                lines.Add(line.Trim());
            }
            string text = "";
            var texts = new List<string>();
            for (int i = 0; i < lines.Count; ++i)
            {
                var line = lines[i];
                text += line;
                if (line.Length == 0 || i + 1 == lines.Count)
                {
                    text = Regex.Replace(text, @"\s+", " ");
                    text = text.ToLower();
                    text = text.Trim();
                    if (text.Length > 0) {
                        texts.Add(text);
                    }
                    text = "";
                }
            }
            return texts;

        }
            static void Main(string[] args)
        {
            string inputPath = args[0];
            string outputPath = args[0] + ".realty";
            var texts = ReadTestCases(inputPath);

            using (StreamWriter outputFile = new StreamWriter(outputPath))
            {
                foreach (string text in texts)
                {
                    var parser = new AntlrRealtyParser();
                    foreach (var realty in parser.Parse(text))
                    {
                        outputFile.WriteLine(realty.GetJsonString());
                    }
                    outputFile.WriteLine("");
                }
            }
        }
    }
}
