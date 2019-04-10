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

        private XElement IncomeToXml()
        {
            var res = new XElement("income");
            if (DeclaredYearlyIncome == null)
            {
                res.Add(XmlHelpers.Nil());
            }
            else
            {
                res.Value = DeclaredYearlyIncome.Value.ToString(DefaultCulture);
            }

            return res;
        }

        private XElement IncomeCommentsToXml()
        {
            return new XElement("incomeComment", XmlHelpers.Nil());
        }

        private XElement IncomeSourcesToXml()
        {
            var res = new XElement("incomeSource");
            if (String.IsNullOrWhiteSpace(DataSources))
            {
                res.Add(XmlHelpers.Nil());
            }
            else
            {
                res.Value = DataSources;
            }

            return res;
        }

    }
}
