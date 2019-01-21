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
        public List<Vechicle> Vehicles = new List<Vechicle>();

        public decimal? DeclaredYearlyIncome;

        public string DataSources = "";


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
