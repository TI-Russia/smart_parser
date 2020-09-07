using System.Collections.Generic;

namespace SmartAntlr
{
    public class OwnTypeListVisitor : OwnTypeListParserBaseVisitor<object> 
    { 
    
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public GeneralAntlrParserWrapper Parser;

        public OwnTypeListVisitor(GeneralAntlrParserWrapper parser)
        {
            Parser = parser;
        }
        public override object VisitOwn_type(OwnTypeListParser.Own_typeContext context)
        {
            var item = new GeneralParserPhrase(Parser, context);
            Lines.Add(item);
            return item;
        }
    }


    public class AntlrOwnTypeParser : GeneralAntlrParserWrapper
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new OwnTypeListParser(CommonTokenStream, Output, ErrorOutput);
            var context = parser.own_type_list();
            var visitor = new OwnTypeListVisitor(this);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}