using System;
using System.Collections.Generic;
using Antlr4.Runtime;

namespace SmartAntlr
{

    public class SquareListVisitor : SquareListBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParserWrapper ParserWrapper;

        public SquareListVisitor(GeneralAntlrParserWrapper parser)
        {
            ParserWrapper = parser;
        }
        public override object VisitBareScore(SquareList.BareScoreContext context)
        {
            int start = context.Start.StartIndex;
            int end = context.Stop.StopIndex;
            string debug = context.ToStringTree(ParserWrapper.Parser);
            var line = new GeneralParserPhrase(ParserWrapper, context);
            Lines.Add(line);
            return line;
        }
    }


    public class AntlrSquareParser : GeneralAntlrParserWrapper
    {
    
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new SquareList(CommonTokenStream, Output, ErrorOutput);
            Parser = parser;
            parser.ErrorHandler = new BailErrorStrategy();
            try
            {
                var context = parser.bareSquares();
                var visitor = new SquareListVisitor(this);
                visitor.Visit(context);
                return visitor.Lines;
            }
            catch (Antlr4.Runtime.Misc.ParseCanceledException e)
            {
                return new List<GeneralParserPhrase>();
            }
            catch (RecognitionException e)
            {
                return new List<GeneralParserPhrase>();
            }

        }



    }
}