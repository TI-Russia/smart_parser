using System.Collections.Generic;
using System.Text.RegularExpressions;
using SmartAntlr;
using System.IO;

public class AntlrTestUtilities
{
    public static List<string> ReadTestCases(string inputPath)
    {
        var lines = new List<string>();
        foreach (string line in File.ReadLines(inputPath))
        {
            lines.Add(line + "\n");
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
                if (text.Length > 0)
                {
                    texts.Add(text);
                }
                text = "";
            }
        }
        return texts;

    }
    public static void ProcessTestCases(List<string> texts, string outputPath)
    {
        using (StreamWriter outputFile = new StreamWriter(outputPath))
        {
            foreach (string text in texts)
            {
                outputFile.WriteLine(text);
                foreach (var realty in AntlrRealtyParser.Parse(text))
                {
                    outputFile.WriteLine(realty.GetJsonString());
                }
                outputFile.WriteLine("");
            }
        }
    }

}