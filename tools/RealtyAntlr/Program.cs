using System;
using System.IO;

namespace SmartAntlr
{

    class Program
    {
        static void Main(string[] args)
        {
            string inputPath = args[0];
            string outputPath = args[0] + ".realty";
            using (StreamWriter outputFile = new StreamWriter(outputPath))
            {
                foreach (string text in File.ReadLines(inputPath))
                {
                    var parser = new AntlrRealtyParser();
                    foreach (var realty in parser.Parse(text))
                    {
                        outputFile.WriteLine(realty.GetJsonString());
                    }
                }
            }
        }
    }
}
