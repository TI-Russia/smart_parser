using System.Collections.Generic;
using Antlr4.Runtime;
using Newtonsoft.Json;
using TI.Declarator.ParserCommon;
using System.Text.RegularExpressions;
using System;
using System.IO;

namespace SmartAntlr
{
    public class CountryFromText
    {
        public string Country = "";

        public CountryFromText(string inputText, CountryListParser.CountryContext context)
        {
            Country = context.GetText();
        }
        public string GetJsonString()
        {
            var my_jsondata = new Dictionary<string, string>
            {
                { "Country", Country}
            };
            return JsonConvert.SerializeObject(my_jsondata, Formatting.Indented);
        }
    }

    public class CountryListVisitor : CountryListParserBaseVisitor<object>
    {
        public List<CountryFromText> Lines = new List<CountryFromText>();
        public string InputText;

        public CountryListVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitCountry(CountryListParser.CountryContext context)
        {
            var line = new CountryFromText(InputText, context);
            Lines.Add(line);
            return line;
        }
    }


    public class AntlrCountryParser : GeneralRealtyParser
    {
        public List<CountryFromText> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new CountryListParser(CommonTokenStream);
            var context = parser.countries();
            var visitor = new CountryListVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }

        public override List<string> ParseToJson(string inputText)
        {
            var result = new List<string>();
            foreach (var i in Parse(inputText))
            {
                result.Add(i.GetJsonString());
            }
            return result;
        }

    }
}