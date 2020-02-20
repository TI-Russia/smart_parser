using AngleSharp.Dom;
using System;
using System.Collections.Generic;
using System.Text;
using System.Linq;
using System.Text.RegularExpressions;

namespace Smart.Parser.Lib.Adapters.HtmlSchemes
{
    class ArbitrationCourtMariEl: ArbitrationCourt1
    {
        #region consts
        protected static Regex _yearMatcher = new Regex(@"\d+\s*год", RegexOptions.Compiled | RegexOptions.IgnoreCase);
        #endregion

        public override bool CanProcess(IDocument document)
        {
            try
            {
                var selection = document.QuerySelectorAll("table.main-table");
                return selection.Length > 0;
            }catch(Exception)
            {
                return false;
            }
        }


        public override string GetPersonName()
        {
            var selection = this.Document.QuerySelector("div.b-cardHeader").QuerySelector("h2");
            string name = selection.TextContent;
            return RemoveNewLineSymbols(name);

        }

        public override List<int> GetYears()
        {
            var selection = Document.QuerySelector("table.b-cardTabs");
            var links = selection.QuerySelectorAll("span").
                                    Where(x => x.TextContent.
                                    Contains("год"));

            List<int> years = links.Select(x => x.TextContent).
                                      Select(x => _yearMatcher.Match(x)).
                                      Where(x => x.Success).Select(x => x.Value).
                                      Select(x => _intMatcher.Match(x).Value).
                                      Select(x=>int.Parse(x)).
                                      ToList();
            return years;
        }

        public override IElement GetTableFromMember(IElement memberElement)
        {
            return memberElement;
        }



    }
}
