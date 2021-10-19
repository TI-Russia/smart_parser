using SmartParser.Lib;
using StringHelpers;

using AngleSharp.Dom;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Document = DocumentFormat.OpenXml.Wordprocessing.Document;

namespace SmartParser.Lib
{
    public abstract class IAdapterScheme
    {
        #region const

        protected const string NAME_COLUMN = "ФИО";
        protected const string COLUMN_INCOME = "Доход";
        protected const string REAL_ESTATE_TYPE = "Вид недвижимости в собственности";
        protected const string REAL_ESTATE_SQUARE = "Площадь в собственности (кв.м)";
        protected const string REAL_ESTATE_COUTRY = "Страна расположения имущества в собственности";
        protected const string STATE_ESTATE_TYPE = "Вид недвижимости в пользовании";
        protected const string STATE_ESTATE_SQUARE = "Площадь в пользовании (кв.м)";
        protected const string STATE_ESTATE_COUTRY = "Страна расположения имущества в пользовании";
        protected const string VEHICLES_TYPE = "Транспортные средства, вид";
        protected const string VEHICLES_NAME = "Транспортные средства, марка";

        #endregion

        #region fields
        #endregion

        public Document Document { get; set; }
        public abstract bool CanProcess(WordprocessingDocument document);
        
        public abstract Declaration Parse(Parser parser, int? userDocumentFileId);
    }
}