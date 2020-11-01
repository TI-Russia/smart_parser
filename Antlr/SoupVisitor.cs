using System;
using System.Collections.Generic;
using Antlr4.Runtime;

namespace SmartAntlr
{

    public class SoupVisitor : SoupBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParserWrapper ParserWrapper;

        public SoupVisitor(GeneralAntlrParserWrapper parser)
        {
            ParserWrapper = parser;
        }
        RealtyFromText InitializeOneRecord(Soup.Any_realty_itemContext  context)
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
                record.InitializeSquare(sc.square_value().GetText(), sc.HECTARE() != null);
            }
            if (context.own_type() != null && context.own_type().realty_share() != null)
            {
                record.RealtyShare = context.own_type().realty_share().GetText();
            }
            if (context.country() != null)
            {
                record.Country = ParserWrapper.GetSourceTextByParserContext(context.country());
            }
            return record;
        }

        public override object VisitAny_realty_item(Soup.Any_realty_itemContext context)
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
            var parser = new Soup(CommonTokenStream, Output, ErrorOutput);
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