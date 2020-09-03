using System.Collections.Generic;
using Antlr4.Runtime;
using Newtonsoft.Json;

namespace SmartAntlr
{
    public class RealtyFromText
    {
        public string OwnType = "";
        public string RealtyType = "";
        public string Square = "";
        public string RealtyShare = "";
        public string Country = "";

        public RealtyFromText(RealtyParser.RealtyContext context)
        {
            if (context.own_type() != null)
            {
                OwnType = context.own_type().OWN_TYPE().GetText();
            }
            if (context.realty_type() != null)
            {
                RealtyType = context.realty_type().REALTY_TYPE().GetText();
            }
            
            if (context.square() != null)
            {
                RealtyParser.SquareContext sc = context.square();
                Square = sc.NUMBER().GetText();
            }
            if (context.own_type() != null && context.own_type().realty_share() != null)
            {
                RealtyShare = context.own_type().realty_share().GetText();
            }
            if (context.COUNTRY() != null)
            {
                Country = context.COUNTRY().GetText();
            }
            
        }
        public string GetJsonString()
        {
            var my_jsondata = new Dictionary<string, string>
            {
                { "OwnType", OwnType},
                { "RealtyType",  RealtyType},
                { "Square", Square}
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