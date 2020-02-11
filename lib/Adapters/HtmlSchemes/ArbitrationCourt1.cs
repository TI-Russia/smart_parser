using AngleSharp.Dom;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace Smart.Parser.Lib.Adapters.HtmlSchemes
{
    class ArbitrationCourt1 : IHtmlScheme
    {
        

        public override bool CanProcess(IDocument document)
        {
            try
            {
                var selection = document.QuerySelectorAll("div.js-income-member-data");
                
                return selection.Length > 0;
            }
            catch (Exception)
            {
                return false;
            }
        }



        public override string GetMemberName(IElement memberElement)
        {
            return memberElement.QuerySelectorAll("h2.income-member").First().Text();
        }



        public override IHtmlCollection<IElement> GetMembers(IDocument document, string name, string year)
        {
            var tableElement = document.All.Where(x => x.LocalName == "div" && x.Attributes.Any(y => y.Name == "rel" && y.Value == year)).First();
            var members = tableElement.Children;
            return members;
        }



        public override string GetPersonName(IDocument document)
        {
            var selection = document.QuerySelectorAll("h2.b-card-fio");
            var name = selection.First().TextContent;
            return RemoveNewLineSymbols(name);
        }



        public override IElement GetTableFromMember(IElement memberElement)
        {
            return memberElement.QuerySelectorAll("table").First();
        }



        public override string GetTitle(IDocument document, string year)
        {
            string rawTitle = document.All.Where(x => x.LocalName == "title").First().TextContent;
            rawTitle = $"Сведения об имуществе {rawTitle} на период {year}";
            return RemoveNewLineSymbols(rawTitle);
        }



        public override string GetMaxYear(IDocument document)
        {
            return GetYears(document).Max().ToString();
        }



        public override List<int> GetYears(IDocument document)
        {
            List<int> years = new List<int>();
            var selection = document.QuerySelectorAll("li.b-income-year-item");
            foreach (var yearElement in selection)
            {
                int currYear = int.Parse(yearElement.TextContent);
                years.Add(currYear);
            }
            return years;
        }
    }
}
