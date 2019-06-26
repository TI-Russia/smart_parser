using System;
using System.Globalization;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class RealEstateProperty
    {
        public decimal? square { set; get; }

        public string square_raw { set; get; }
        public string country_raw { set; get; }
        public string type_raw { set; get; }
        public string own_type_raw { set; get; }
        public string own_type_by_column { set; get; }

        public string Text { set; get; }

        public RealEstateProperty()
        {}

    }
}
