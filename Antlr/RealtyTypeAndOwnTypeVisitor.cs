using System.Collections.Generic;
using Newtonsoft.Json;

namespace SmartAntlr
{
    public class RealtyTypeAndOwnTypeFromText : GeneralParserPhrase
    {
        public string RealtyType = "";
        public string OwnType = "";
        public string RealtyShare = "";

        public RealtyTypeAndOwnTypeFromText(GeneralAntlrParser parser, RealtyTypeAndOwnTypeParser.RealtyContext context) : 
            base(parser, context)
        {
            if (context.own_type() != null)
            {
                OwnType = context.own_type().OWN_TYPE().GetText();
            }
            if (context.realty_type() != null)
            {
                RealtyType = context.realty_type().REALTY_TYPE().GetText();
            }
            
            if (context.own_type() != null && context.own_type().realty_share() != null)
            {
                RealtyShare = context.own_type().realty_share().GetText();
            }
            if (context.realty_share() != null)
            {
                RealtyShare = context.realty_share().GetText();
            }
        }
        public override string GetJsonString()
        {
            var my_jsondata = new Dictionary<string, string>
            {
                { "OwnType", OwnType},
                { "RealtyType",  RealtyType},
            };
            if (RealtyShare != "")
            {
                my_jsondata["RealtyShare"] = RealtyShare;
            }
            return JsonConvert.SerializeObject(my_jsondata, Formatting.Indented);
        }
    }

    public class RealtyTypeAndOwnTypeVisitor : RealtyTypeAndOwnTypeParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParser Parser;

        public RealtyTypeAndOwnTypeVisitor(GeneralAntlrParser parser)
        {
            Parser = parser;
        }
        public override object VisitRealty(RealtyTypeAndOwnTypeParser.RealtyContext context)
        {
            var line = new RealtyTypeAndOwnTypeFromText(Parser, context);
            Lines.Add(line);
            return line;
        }
    }

    public class AntlrRealtyTypeAndOwnTypeParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new RealtyTypeAndOwnTypeParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.realty_list();
            var visitor = new RealtyTypeAndOwnTypeVisitor(this);
            visitor.Visit(context);
            return visitor.Lines;
        }

    }
}