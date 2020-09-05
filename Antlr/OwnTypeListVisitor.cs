using System.Collections.Generic;

namespace SmartAntlr
{
    public class OwnTypeListVisitor : OwnTypeListParserBaseVisitor<object> 
    { 
    
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public string InputText;

        public OwnTypeListVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitOwn_type(OwnTypeListParser.Own_typeContext context)
        {
            var item = new GeneralParserPhrase(InputText, context);
            Lines.Add(item);
            return item;
        }
    }


    public class AntlrOwnTypeParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new OwnTypeListParser(CommonTokenStream);
            var context = parser.own_type_list();
            var visitor = new OwnTypeListVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}