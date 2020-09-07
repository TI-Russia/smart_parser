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
        
    public GeneralParserPhrase(GeneralAntlrParserWrapper parser, ParserRuleContext context)
    {
        SourceText = parser.GetSourceTextByParserContext(context);
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

public class RealtyFromText : GeneralParserPhrase
{
    public string OwnType = "";
    public string RealtyType = "";
    public decimal Square = -1;
    public string RealtyShare = "";
    public string Country = "";

    public bool IsEmpty()
    {
        return Square == -1 && OwnType.Length == 0 && RealtyType.Length == 0 && RealtyShare.Length == 0 &&
            Country.Length == 0;
    }

    public RealtyFromText(GeneralAntlrParserWrapper parser, ParserRuleContext context) : base(parser, context) 
    { 
    }
    public override string GetJsonString()
    {
        var my_jsondata = new Dictionary<string, string>
            {
                { "OwnType", OwnType},
                { "RealtyType",  RealtyType},
                { "Square", Square.ToString()}
            };
        if (RealtyShare != "")
        {
            my_jsondata["RealtyShare"] = RealtyShare;
        }
        if (Country != "")
        {
            my_jsondata["Country"] = Country;
        }
        return JsonConvert.SerializeObject(my_jsondata, Formatting.Indented);
    }
}

public abstract class GeneralAntlrParserWrapper
{
    public string InputTextCaseSensitive;
    protected CommonTokenStream CommonTokenStream;
    protected TextWriter Output = TextWriter.Null;
    protected TextWriter ErrorOutput = TextWriter.Null;
    public Parser Parser = null;
    public GeneralAntlrParserWrapper(bool silent = true)
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

    public virtual Lexer CreateLexer(AntlrInputStream inputStream)
    {
        return new StrictLexer(inputStream, Output, ErrorOutput);
    }

    public void InitLexer(string inputText)
    {
        inputText = Regex.Replace(inputText, @"\s+", " ");
        inputText = inputText.Trim();
        InputTextCaseSensitive = inputText;
        AntlrInputStream inputStream = new AntlrInputStream(InputTextCaseSensitive.ToLower());
        var lexer = CreateLexer(inputStream);
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

    public string GetSourceTextByParserContext(ParserRuleContext context)
    {
        int start = context.Start.StartIndex;
        int end = InputTextCaseSensitive.Length;
        if (context.Stop != null)
        {
            end = context.Stop.StopIndex + 1;
        }
        if (end > start)
        {
            return InputTextCaseSensitive.Substring(start, end - start);
        }
        else
        {
            return context.GetText();
        }
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
            if (line.Trim().Length == 0 || i + 1 == lines.Count)
            {
                text = Regex.Replace(text, @"\s+", " ");
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
    public static void WriteTestCaseResultsToFile(GeneralAntlrParserWrapper parser, List<string> texts, string outputPath)
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