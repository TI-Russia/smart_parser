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

        // better to use Row reference here
        public HashSet<int> InputRowIndices = new HashSet<int>();

        public string document_position { set; get; }
        virtual public int? PersonIndex { set; get; } = null;
    }
}
