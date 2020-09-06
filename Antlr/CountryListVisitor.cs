using System.Collections.Generic;

namespace SmartAntlr
{

    public class CountryListVisitor : CountryListParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public string InputText;

        public CountryListVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitCountry(CountryListParser.CountryContext context)
        {
            var line = new GeneralParserPhrase(InputText, context);
            Lines.Add(line);
            return line;
        }
    }


    public class AntlrCountryParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new CountryListParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.countries();
            var visitor = new CountryListVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}