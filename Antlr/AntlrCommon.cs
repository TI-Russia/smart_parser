using System.Collections.Generic;
using System.Text.RegularExpressions;
using SmartAntlr;
using System.IO;
using Antlr4.Runtime;
using System;
using Newtonsoft.Json;


public class GeneralParserPhrase
{
    string TextFromLexer = "";
    string SourceText = "";

    public GeneralParserPhrase(string inputText, ParserRuleContext context)
    {
        int start = context.Start.StartIndex;
        int end = inputText.Length;
        if (context.Stop != null)
        {
            end = context.Stop.StopIndex + 1;
        }
        if (end > start)
        {
            SourceText = inputText.Substring(start, end - start);
        }
        TextFromLexer = context.GetText();
    }

    virtual public string GetJsonString()
    {
        var my_jsondata = new Dictionary<string, string>
            {
                { "value", TextFromLexer}
            };
        return JsonConvert.SerializeObject(my_jsondata, Formatting.Indented);
    }


    public string GetText() { return TextFromLexer; }
    public string GetSourceText() { return SourceText; }

}

public abstract class GeneralAntlrParser
{
    protected string InputText;
    protected CommonTokenStream CommonTokenStream;
    protected TextWriter Output = TextWriter.Null;
    protected TextWriter ErrorOutput = TextWriter.Null;

    public GeneralAntlrParser(bool silent = true)
    {
        if (!silent)
        {
            BeVerbose();
        }
    }
    public void BeVerbose()
    {
        Output = Console.Out;
        ErrorOutput = Console.Error;
    }
    public void InitLexer(string inputText)
    {
        inputText = Regex.Replace(inputText, @"\s+", " ");
        inputText = inputText.Trim();
        InputText = inputText;
        AntlrInputStream inputStream = new AntlrInputStream(InputText.ToLower());
        RealtyLexer lexer = new RealtyLexer(inputStream, Output, ErrorOutput);
        CommonTokenStream = new CommonTokenStream(lexer);
    }
    public abstract List<GeneralParserPhrase> Parse(string inputText);

    public List<string> ParseToJson(string inputText)
    {
        var result = new List<string>();
        if (inputText != null)
        {
            foreach (var i in Parse(inputText))
            {
                result.Add(i.GetJsonString());
            }
        }
        return result;
    }

    public List<string> ParseToStringList(string inputText)
    {
        var result = new List<string>();
        if (inputText != null)
        {
            foreach (var item in Parse(inputText))
            {
                if (item.GetText() != "")
                {
                    result.Add(item.GetText());
                }
            }
        }
        return result;

    }

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
    public static void WriteTestCaseResultsToFile(GeneralAntlrParser parser, List<string> texts, string outputPath)
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