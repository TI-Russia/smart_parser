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
                res.Append("\n");
            }

            if (Unbastardize)
            {
                return res.ToString().Unbastardize();
            }
            return res.ToString();
        }

        /// <summary>
        /// Removes translit and whitespace glitches commonly found in declaration fields
        /// </summary>
        /// <param name="str"></param>
        /// <returns></returns>
        public static string Unbastardize(this string str)
        {
            return str.ToString().RemoveStupidTranslit().Replace("  ", " ").Trim();
        }

        /// <summary>
        /// Get plaintext-with-separators representation for given row
        /// </summary>
        /// <param name="r"></param>
        public static string Stringify(this Xceed.Words.NET.Row r)
        {
            var resSb = new StringBuilder();

            foreach (var c in r.Cells)
            {
                resSb.Append(c.GetText());
                resSb.Append(" | ");
            }

            return resSb.ToString();
        }
    }
}
