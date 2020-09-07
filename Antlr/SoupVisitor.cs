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
        public GeneralAntlrParserWrapper ParserWrapper;

        public SoupVisitor(GeneralAntlrParserWrapper parser)
        {
            ParserWrapper = parser;
        }
        RealtyFromText InitializeOneRecord(SoupParser.Any_realty_itemContext  context)
        {
            var record = new RealtyFromText(ParserWrapper, context);
            if (context.own_type() != null)
            {
                record.OwnType = context.own_type().OWN_TYPE().GetText();
            }
            if (context.realty_type() != null)
            {
                record.RealtyType = context.realty_type().REALTY_TYPE().GetText();
            }

            if (context.square() != null && context.square().square_value() != null)
            {
                var sc = context.square();
                var strVal = sc.square_value().GetText();
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
                // record.Country = context.country().GetText();
                record.Country = ParserWrapper.GetSourceTextByParserContext(context.country());
            }
            return record;
        }

        public override object VisitAny_realty_item(SoupParser.Any_realty_itemContext context)
        {
            string debug = context.ToStringTree(ParserWrapper.Parser);
            var line = InitializeOneRecord(context);
            if (!line.IsEmpty())
            {
                Lines.Add(line);
            }
            return line;
        }
    }

    public class AntlrSoupParser : GeneralAntlrParserWrapper
    {
        public override Lexer CreateLexer(AntlrInputStream inputStream)
        {
            return new SoupLexer(inputStream, Output, ErrorOutput);
        }

        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new SoupParser(CommonTokenStream, Output, ErrorOutput);
            //parser.Trace = true;
            Parser = parser;
            // parser.ErrorHandler = new BailErrorStrategy();
            ///parser.ErrorHandler = new MyGrammarErrorStrategy();
            try
            {
                var context = parser.any_realty_item_list();
                var visitor = new SoupVisitor(this);
                visitor.Visit(context);
                return visitor.Lines;
            }
            catch (RecognitionException e)
            {
                return new List<GeneralParserPhrase>();
            }
        }


    }
}