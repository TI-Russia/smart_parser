using System.Collections.Generic;

namespace SmartAntlr
{

    public class SquareListVisitor : SquareListParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParser Parser;

        public SquareListVisitor(GeneralAntlrParser parser)
        {
            Parser = parser;
        }
        public override object VisitSquare(SquareListParser.SquareContext context)
        {
            var line = new GeneralParserPhrase(Parser, context);
            Lines.Add(line);
            return line;
        }
    }


    public class AntlrSquareParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new SquareListParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.squares();
            var visitor = new SquareListVisitor(this);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}