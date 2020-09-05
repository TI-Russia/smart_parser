using System.Collections.Generic;

namespace SmartAntlr
{
    public class RealtyTypeListVisitor : RealtyTypeListParserBaseVisitor<object> 
    { 
    
        public List<GeneralParserPhrase> Lines = new List<GeneralParserPhrase>();
        public string InputText;

        public RealtyTypeListVisitor(string inputText)
        {
            InputText = inputText;
        }
        public override object VisitRealty_type(RealtyTypeListParser.Realty_typeContext context)
        {
            var item = new GeneralParserPhrase(InputText, context);
            Lines.Add(item);
            return item;
        }
    }


    public class AntlrRealtyTypeParser : GeneralAntlrParser
    {
        public override List<GeneralParserPhrase> Parse(string inputText)
        {
            InitLexer(inputText);
            var parser = new RealtyTypeListParser(CommonTokenStream);
            var context = parser.realty_type_list();
            var visitor = new RealtyTypeListVisitor(InputText);
            visitor.Visit(context);
            return visitor.Lines;
        }


    }
}