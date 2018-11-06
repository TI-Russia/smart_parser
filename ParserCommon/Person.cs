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

        public IEnumerable<XElement> ContentsToXml()
        {
            List<XElement> contentsXml = new List<XElement>();
            contentsXml.Add(RealEstateToXml());
            contentsXml.Add(VehiclesToXml());
            contentsXml.Add(IncomeToXml());
            contentsXml.Add(IncomeCommentsToXml());
            contentsXml.Add(IncomeSourcesToXml());
            return contentsXml;
        }

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

        private XElement RealEstateToXml()
        {
            var res = new XElement("realties");
            if (RealEstateProperties.Count == 0)
            {
                res.Add(XmlHelpers.Nil());
            }
            else
            {
                foreach (var prop in RealEstateProperties)
                {
                    res.Add(prop.ToXml());
                }
            }

            return res;
        }

        private XElement VehiclesToXml()
        {
            var res = new XElement("transports");
            if (Vehicles.Count == 0)
            {
                res.Add(XmlHelpers.Nil());
            }
            else
            {
                foreach (var vehicle in Vehicles)
                {
                    res.Add(new XElement("transport",
                              new XElement("transportName", vehicle)));
                }
            }

            return res;
        }
    }
}
