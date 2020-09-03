using System.Collections.Generic;
using Antlr4.Runtime;
using Newtonsoft.Json;

namespace SmartAntlr
{
    public class RealtyFromText
    {
        public string OwnType;
        public string RealtyType;
        public string Square;
        public RealtyFromText(RealtyParser.RealtyContext context)
        {
            if (context.OWN_TYPE() != null)
            {
                OwnType = context.OWN_TYPE().GetText();
            }
            if (context.REALTY_TYPE() != null)
            {
                RealtyType = context.REALTY_TYPE().GetText();
            }
            if (context.square() != null)
            {
                RealtyParser.SquareContext sc = context.square();
                Square = sc.NUMBER().GetText();
            }
        }
        public string GetJsonString()
        {
            var my_jsondata = new
            {
                OwnType = OwnType,
                RealtyType = RealtyType,
                Square = Square
            };
            return JsonConvert.SerializeObject(my_jsondata, Formatting.Indented);
        }
    }

    public class RealtyVisitor : RealtyParserBaseVisitor<object>
    {
        public List<RealtyFromText> Lines = new List<RealtyFromText>();

        public override object VisitRealty(RealtyParser.RealtyContext context)
        {
            var line = new RealtyFromText(context);
            Lines.Add(line);
            return line;
        }
    }

    public class AntlrRealtyParser
    {
        public List<RealtyFromText> Parse(string inputText)
        {
            AntlrInputStream inputStream = new AntlrInputStream(inputText);
            RealtyLexer speakLexer = new RealtyLexer(inputStream);
            CommonTokenStream commonTokenStream = new CommonTokenStream(speakLexer);
            RealtyParser speakParser = new RealtyParser(commonTokenStream);

            var context = speakParser.realty_list();
            var visitor = new RealtyVisitor();
            visitor.Visit(context);
            return visitor.Lines;
        }
    }
}