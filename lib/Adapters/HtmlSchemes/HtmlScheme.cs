using AngleSharp.Dom;
using Aspose.Cells;
using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;

namespace SmartParser.Lib
{
    public abstract class IHtmlScheme
    {
        #region const
        protected Regex _intMatcher = new Regex(@"\d+", RegexOptions.Compiled);
        #endregion
        public IDocument Document{ get; set; }


        public abstract IEnumerable<IElement> GetMembers(string name, string year);
        public abstract string GetTitle(string year);
        public abstract string GetMaxYear();
        public abstract List<int> GetYears();
        public abstract string GetPersonName();
        public abstract string GetMemberName(IElement memberElement);
        public abstract IElement GetTableFromMember(IElement memberElement);
        public abstract bool CanProcess(IDocument document);

        protected static string RemoveNewLineSymbols(string line)
        {
            line = line.Replace("\n", "").Replace("\t", "");
            return line;
        }

        public abstract void ModifyHeaderForAdditionalFields(List<string> headerLine);

        public abstract void ModifyLinesForAdditionalFields(List<List<string>> tableLines, bool isMainDeclarant = false);


    }
}
