using System.Collections.Generic;

namespace SmartAntlr
{

    public class SquareListVisitor : SquareListParserBaseVisitor<object>
    {
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public string InputText;

        public SquareListVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitSquare(SquareListParser.SquareContext context)
        {
            var line = new GeneralParserPhrase(InputText, context);
            Lines.Add(line);
            return line;
        }
    }


    public class AntlrSquareParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new SquareListParser(CommonTokenStream);
            var context = parser.squares();
            var visitor = new SquareListVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}