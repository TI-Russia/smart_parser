using Smart.Parser.Adapters;
using AngleSharp.Dom;
using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using DocumentFormat.OpenXml.Packaging;

namespace Smart.Parser.Lib.Adapters.DocxSchemes
{
    public abstract class IDocxScheme
    {
        #region const
        protected Regex _intMatcher = new Regex(@"\d+", RegexOptions.Compiled);
        #endregion

        #region fields
        protected string Title = "";
        #endregion
        
        public WordprocessingDocument Document{ get; set; }
        public abstract string GetTitle();
        public abstract string GetPersonName();
        public abstract bool CanProcess(WordprocessingDocument document);

        public abstract void ProcessMainPerson(string name, OnePersonAdapter adapter);

        
    }
}
