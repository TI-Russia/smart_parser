using System;
using System.Linq;
using System.Text;

using Xceed.Words.NET;


namespace TI.Declarator.WordParser
{
    public static class DocXHelpers
    {
        public static string GetText(this Cell c)
        {
            var res = new StringBuilder();
            foreach (var p in c.Paragraphs)
            {
                res.Append(p.Text);
                res.Append(" ");
            }

            return res.ToString();
        }
    }
}
