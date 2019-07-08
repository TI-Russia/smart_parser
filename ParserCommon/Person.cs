using System;
using System.Collections.Generic;
using System.Globalization;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public abstract class Person
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;

        public List<RealEstateProperty> RealEstateProperties = new List<RealEstateProperty>();
        public List<Vehicle> Vehicles = new List<Vehicle>();

        public decimal? DeclaredYearlyIncome;

        public string DataSources = "";

        public int RangeLow { set; get; }
        public int RangeHigh { set; get; }

        public string document_position { set; get; }
    }
}
