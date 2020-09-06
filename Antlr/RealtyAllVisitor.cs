using System.Collections.Generic;
using Antlr4.Runtime;
using Newtonsoft.Json;
using TI.Declarator.ParserCommon;
using System.Text.RegularExpressions;
using System;
using System.IO;

namespace SmartAntlr
{
    public class RealtyFromText : GeneralParserPhrase
    {
        public string OwnType = "";
        public string RealtyType = "";
        public decimal Square = -1;
        public string RealtyShare = "";
        public string Country = "";

        public RealtyFromText(string inputText, RealtyAllParser.RealtyContext context) : base(inputText, context)
        {
            if (context.own_type() != null)
            {
                OwnType = context.own_type().OWN_TYPE().GetText();
            }
            if (context.realty_type() != null)
            {
                RealtyType = context.realty_type().REALTY_TYPE().GetText();
            }
            
            if (context.square() != null && context.square().NUMBER() != null)
            {
                RealtyAllParser.SquareContext sc = context.square();
                var strVal = sc.NUMBER().GetText(); 
                Square = strVal.ParseDecimalValue(); 
                if (sc.HECTARE() != null)
                {
                    Square = Square * 10000;
                }
            }
            if (context.own_type() != null && context.own_type().realty_share() != null)
            {
                RealtyShare = context.own_type().realty_share().GetText();
            }
            if (context.realty_share() != null)
            {
                RealtyShare = context.realty_share().GetText();
            }
            if (context.COUNTRY() != null)
            {
                Country = context.COUNTRY().GetText();
            }
            
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

    public class RealtyVisitor : RealtyAllParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public string InputText;

        public RealtyVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitRealty(RealtyAllParser.RealtyContext context)
        {
            var line = new RealtyFromText(InputText, context);
            Lines.Add(line);
            return line;
        }
    }

    public class AntlrRealtyParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new RealtyAllParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.realty_list();
            var visitor = new RealtyVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }

    }
}