using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using TI.Declarator.ParserCommon;
using Antlr4.Runtime;

namespace SmartAntlr
{

    public class SoupVisitor : SoupParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParser Parser;

        public SoupVisitor(GeneralAntlrParser parser)
        {
            Parser = parser;
        }
        RealtyFromText InitializeOneRecord(SoupParser.Any_realty_itemContext  context)
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
            if (context.country() != null)
            {
                record.Country = context.country().GetText();
            }
            return record;
        }

        public override object VisitAny_realty_item(SoupParser.Any_realty_itemContext context)
        {
            var line = InitializeOneRecord(context);
            if (!line.IsEmpty())
            {
                Lines.Add(line);
            }
            return line;
        }
    }

    public class AntlrSoupParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText, false);
            var parser = new SoupParser(CommonTokenStream, Output, ErrorOutput);
            // parser.ErrorHandler = new BailErrorStrategy();
            ///parser.ErrorHandler = new MyGrammarErrorStrategy();
            try
            {
                var context = parser.any_realty_item_list();
                var visitor = new SoupVisitor(this);
                visitor.Visit(context);
                return visitor.Lines;
            }
            catch (Exception e)
            {
                return new List<GeneralParserPhrase>();
            }
        }


    }
}