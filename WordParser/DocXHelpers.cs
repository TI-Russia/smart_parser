using System;
using System.Text;

using Xceed.Words.NET;

using TI.Declarator.ParserCommon;


namespace TI.Declarator.WordParser
{
    public static class DocXHelpers
    {
        public static string GetText(this Cell c, bool Unbastardize = false)
        {
            var res = new StringBuilder();
            foreach (var p in c.Paragraphs)
            {
                res.Append(p.Text);
                res.Append(" ");
            }

            if (Unbastardize)
            {
                return res.ToString().RemoveStupidTranslit().Replace("  ", " ").Trim();
            }
            return res.ToString();
        }
    }
}
