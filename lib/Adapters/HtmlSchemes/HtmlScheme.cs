using AngleSharp.Dom;
using System;
using System.Collections.Generic;
using System.Text;

namespace Smart.Parser.Lib.Adapters.HtmlSchemes
{
    public abstract class IHtmlScheme
    {
        public abstract IHtmlCollection<IElement> GetMembers(IDocument document, string name, string year);
        public abstract string GetTitle(IDocument document, string year);
        public abstract string GetYear(IDocument document);
        public abstract string GetPersonName(IDocument document);
        public abstract string GetMemberName(IElement memberElement);
        public abstract IElement GetTableFromMember(IElement memberElement);
        public abstract bool CanProcess(IDocument document);

        protected static string RemoveNewLineSymbols(string line)
        {
            line = line.Replace("\n", "").Replace("\t", "");
            return line;
        }

    }
}
