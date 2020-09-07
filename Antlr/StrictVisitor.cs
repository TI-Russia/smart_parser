using System.Collections.Generic;
using Newtonsoft.Json;
using TI.Declarator.ParserCommon;

namespace SmartAntlr
{
    
    public class StrictVisitor : StrictParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParser Parser;

        public StrictVisitor(GeneralAntlrParser parser)
        {
            Parser = parser;
        }
        RealtyFromText InitializeOneRecord(StrictParser.RealtyContext context)
        {
            var record = new RealtyFromText(Parser, context);
            if (context.own_type() != null)
            {
                record.OwnType = context.own_type().OWN_TYPE().GetText();
            }
            if (context.realty_type() != null)
            {
                record.RealtyType = context.realty_type().REALTY_TYPE().GetText();
            }

            if (context.square() != null && context.square().NUMBER() != null)
            {
                var sc = context.square();
                var strVal = sc.NUMBER().GetText();
                record.Square = strVal.ParseDecimalValue();
                if (sc.HECTARE() != null)
                {
                    record.Square = record.Square * 10000;
                }
            }
            if (context.own_type() != null && context.own_type().realty_share() != null)
            {
                record.RealtyShare = context.own_type().realty_share().GetText();
            }
            if (context.realty_share() != null)
            {
                record.RealtyShare = context.realty_share().GetText();
            }
            if (context.COUNTRY() != null)
            {
                record.Country = context.COUNTRY().GetText();
            }
            return record;
        }

        public override object VisitRealty(StrictParser.RealtyContext context)
        {
            var line = InitializeOneRecord(context);
            Lines.Add(line);
            return line;
        }
    }

    public class AntlrStrictParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new StrictParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.realty_list();
            var visitor = new StrictVisitor(this);
            visitor.Visit(context);
            return visitor.Lines;
        }

    }
}