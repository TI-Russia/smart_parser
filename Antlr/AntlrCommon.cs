using System.Collections.Generic;
using System.Text.RegularExpressions;
using SmartAntlr;
using System.IO;
using Antlr4.Runtime;
using System;


public abstract class GeneralRealtyParser
{
    public string InputText;
    public bool Silent = true;
    public CommonTokenStream CommonTokenStream;

    public GeneralRealtyParser(bool silent = true)
    {
        Silent = silent;
    }
    public void InitLexer(string inputText)
    {
        inputText = Regex.Replace(inputText, @"\s+", " ");
        inputText = inputText.Trim();
        InputText = inputText;
        AntlrInputStream inputStream = new AntlrInputStream(InputText.ToLower());
        TextWriter output = Console.Out;
        TextWriter errorOutput = Console.Error;
        if (Silent)
        {
            output = TextWriter.Null;
            errorOutput = TextWriter.Null;
        }
        RealtyLexer lexer = new RealtyLexer(inputStream, output, errorOutput);
        CommonTokenStream = new CommonTokenStream(lexer);
    }
    public abstract List<string> ParseToJson(string inputText);

}

public class AntlrCommon
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
    public static void WriteTestCaseResultsToFile(GeneralRealtyParser parser, List<string> texts, string outputPath)
    {
        using (StreamWriter outputFile = new StreamWriter(outputPath))
        {
            outputFile.NewLine = "\n";
            foreach (string text in texts)
            {
                outputFile.WriteLine(text);
                foreach (var realtyStr in parser.ParseToJson(text))
                {
                    outputFile.WriteLine(realtyStr.Replace("\r", String.Empty));
                }
                outputFile.WriteLine("");
            }
        }
    }

}