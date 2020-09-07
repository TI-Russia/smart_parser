using System.Collections.Generic;

namespace SmartAntlr
{
    public class RealtyTypeListVisitor : RealtyTypeListParserBaseVisitor<object> 
    { 
    
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParserWrapper Parser;

        public RealtyTypeListVisitor(GeneralAntlrParserWrapper parser)
        {
            Parser = parser;
        }
        public override object VisitRealty_type(RealtyTypeListParser.Realty_typeContext context)
        {
            var item = new GeneralParserPhrase(Parser, context);
            Lines.Add(item);
            return item;
        }
    }


    public class AntlrRealtyTypeParser : GeneralAntlrParserWrapper
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new RealtyTypeListParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.realty_type_list();
            var visitor = new RealtyTypeListVisitor(this);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}