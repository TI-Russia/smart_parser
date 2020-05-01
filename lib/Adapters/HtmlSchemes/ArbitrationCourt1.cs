using AngleSharp.Dom;
using Aspose.Cells;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace Smart.Parser.Lib.Adapters.HtmlSchemes
{
    class ArbitrationCourt1 : IHtmlScheme
    {
        #region consts
        protected const string NAME_COLUMN_CAPTION = "ФИО";
        protected const string REAL_ESTATE_CAPTION = "Объекты недвижимости в собственности или пользовании";
        protected const string REAL_ESTATE_SQUARE = "Площадь в собственности или пользовании (кв.м)";
        protected const string REAL_ESTATE_OWNERSHIP = "Вид собственности в пользовании или в праве собственности";
        protected const string REAL_ESTATE_COUNTRY = "Страна";
        protected const string COLLEGIUM_CAPTION = "Коллегия";
        protected const string COLLEGIUM_CAPTION_NAME = "наименование организации";

        #endregion



        #region Regex matchers
        protected static Regex _realEstateMatcher = new Regex(@"\s*Недвижимое\s*имущество\s*(\(\s*кв[\. ]*м\s*\)\s*)?",
                                                               RegexOptions.Compiled | RegexOptions.IgnoreCase);
        protected static Regex _realEstateObjectMatcher = new Regex(@"(?<type>[^\(0-9]+)(?<own_type>\([^\)]+\)+)?[\s-]*(?<square_size>[0-9.,]+(?:\s*кв.\s?м\.?)?)?(?<country>[^0-9]*)?", RegexOptions.Compiled);
        protected static Regex _squareMatcher = new Regex(@"\d+(.\d+)*", RegexOptions.Compiled);
        protected static Regex _ownershipMatcher = new Regex(@"(долевая)*(индивидуальная)*\s*собственность");
        protected static Regex _yearMatcher = new Regex(@"\d+\s*год", RegexOptions.Compiled | RegexOptions.IgnoreCase);
        #endregion

        #region fields
        protected int _realEstateColumnNum = -1;
        protected int _collegiumColumNum = -1;
        protected string _collegium = "";
        #endregion


        #region Logic
        public override bool CanProcess(IDocument document)
        {
            try
            {
                try { 
                    Document = document;
                    var selection = document.QuerySelectorAll("div.js-income-member-data");
                    if (selection.Length == 0) return false;
                    string name = GetPersonName();
                    return !string.IsNullOrEmpty(name) ;
                }
                finally
                {
                    Document = null;
                }
            }
            catch (Exception)
            {
                return false;
            }
        }



        public override string GetMemberName(IElement memberElement)
        {
            var selection = memberElement.QuerySelectorAll("h2.income-member");
            if (selection.Length > 0)
                return RemoveNewLineSymbols(selection.First().Text());

            string name = RemoveNewLineSymbols(memberElement.PreviousSibling.PreviousSibling.TextContent);
            return name;
        }



        public override IEnumerable<IElement> GetMembers( string name, string year)
        {
            IElement tableElement;
            if (year != null)
                tableElement = Document.All.Where(x => x.LocalName == "div" &&
                                                  x.Attributes.Any(y => y.Name == "rel" &&
                                                                   y.Value == year)
                                                  ).First();
            else
                throw new NotImplementedException(); // TODO
            var members = tableElement.Children.Where(x=>x.LocalName == "table" || x.LocalName == "div");
            return members;
        }



        public override string GetPersonName()
        {
            string name;
            var selection = Document.QuerySelectorAll("h2.b-card-fio");
            if (selection.Length > 0)
            {
                name = selection.First().TextContent;
            }
            else
            {
                var nameEl = Document.QuerySelector("div.b-cardHeader").QuerySelector("h2");
                name = nameEl.TextContent;
            }
            return RemoveNewLineSymbols(name);
        }



        public override IElement GetTableFromMember(IElement memberElement)
        {
            var selection = memberElement.QuerySelectorAll("table");
            if (selection.Length > 0)
                return selection.First();
            return memberElement;
        }



        public override string GetTitle(string year)
        {
            
            string rawTitle = Document.All.Where(x => x.LocalName == "title").First().TextContent;
            rawTitle = $"Сведения об имуществе {rawTitle}";
            if (year != null)
                rawTitle = $"{rawTitle}  на период {year}";
            return RemoveNewLineSymbols(rawTitle);
        }



        public override string GetMaxYear()
        {
            return GetYears().Max().ToString();
        }



        public override List<int> GetYears()
        {
            List<int> years = new List<int>();
            var selection = Document.QuerySelectorAll("li.b-income-year-item");
            var divs = Document.QuerySelectorAll("div.js-income-member-data");
            if (selection.Length > 0)
            {
                foreach (var yearElement in selection)
                {
                    int currYear = int.Parse(yearElement.TextContent);
                    years.Add(currYear);
                }
            } else if (divs.Length > 0)
            {
                foreach (var yearElement in divs)
                {
                    int currYear = int.Parse(yearElement.GetAttribute("rel"));
                    years.Add(currYear);
                }
            }
            else
            {
                selection = Document.QuerySelectorAll("table.b-cardTabs");
                if (selection.Length == 0)
                    return years;
                var links = selection.First().QuerySelectorAll("span").
                                              Where(x => x.TextContent.
                                              Contains("год"));

                years = links.Select(x => x.TextContent).
                                          Select(x => _yearMatcher.Match(x)).
                                          Where(x => x.Success).Select(x => x.Value).
                                          Select(x => _intMatcher.Match(x).Value).
                                          Select(x => int.Parse(x)).
                                          ToList();
            }
            return years;
        }



        public override void ModifyHeaderForAdditionalFields(List<string> headerLine)
        {
            ModifyHeaderForRealEstate(headerLine);
            ModifyHeaderForCollegium(headerLine);
        }



        public override void ModifyLinesForAdditionalFields(List<List<string>> tableLines, bool isMainDeclarant)
        {
            ModifyLinesForRealEstate(tableLines);
            ModifyLinesForCollegium(tableLines, isMainDeclarant);
        }



        protected void ModifyHeaderForRealEstate(List<string> headerLine)
        {
            var ind = headerLine.FindIndex(x => _realEstateMatcher.IsMatch(x));
            if (ind >= 0)
            {
                _realEstateColumnNum = ind;
                headerLine[ind] = REAL_ESTATE_CAPTION;
                headerLine.Insert(ind + 1, REAL_ESTATE_SQUARE);
                headerLine.Insert(ind + 2, REAL_ESTATE_OWNERSHIP);
                headerLine.Insert(ind + 3, REAL_ESTATE_COUNTRY);
                
            }
        }


        protected void ModifyLinesForRealEstate(List<List<string>> lines)
        {
            if (_realEstateColumnNum < 0)
                return;
        
            foreach (var line in lines.Skip(1))
            {
                var realEstateText = line[_realEstateColumnNum];

                Match match = _realEstateObjectMatcher.Match(realEstateText);
                if (match.Success)
                {
                    line.Insert(_realEstateColumnNum + 1, match.Groups["square_size"].Value);
                    line.Insert(_realEstateColumnNum + 2, match.Groups["own_type"].Value);
                    line.Insert(_realEstateColumnNum + 3, match.Groups["country"].Value);
                }
                else
                {
                    match = _squareMatcher.Match(realEstateText);
                    line.Insert(_realEstateColumnNum + 1, GetMatchResult(match));
            
                    match = _ownershipMatcher.Match(realEstateText);
                    line.Insert(_realEstateColumnNum + 2, GetMatchResult(match));

                    line.Insert(_realEstateColumnNum + 3, "");
                }
            }
        }


        protected  void ModifyLinesForCollegium(List<List<string>> lines, bool isMain)
        {

            if (_collegiumColumNum == -1)
                return;
            string value;
            if (isMain)
                value = _collegium;
            else
                value = "";
            for(int i = 1; i < lines.Count; i += 1)
            {
                lines[i].Insert(_collegiumColumNum, value);
            }
                
            

        }


        protected void ModifyHeaderForCollegium(List<string> headerLine)
        {
            var selection = Document.All.Where(x => x.LocalName == "dt" &&
                                                      x.ClassList.Contains("b-card-info-caption") &&
                                                      x.TextContent == COLLEGIUM_CAPTION);
            if (selection.Count() <= 0)
                return;
            headerLine.Add(COLLEGIUM_CAPTION_NAME);
            _collegiumColumNum = headerLine.Count-1;
            var tmp = selection.First().ParentElement;
            tmp = tmp.Children[1];
            _collegium = tmp.TextContent;

        }


        protected static string GetMatchResult(Match match)
        {
            if (match.Success)
            {
                return match.Value;
            }

            return "-";
        }

        #endregion




    }
}
