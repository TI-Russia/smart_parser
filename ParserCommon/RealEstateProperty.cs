using System;
using System.Globalization;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class RealEstateProperty
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        public OwnershipType OwnershipType { get; }
        public RealEstateType PropertyType { get; }

        public Country Country { get; }
        public decimal? Area { get; }
        public string OwnedShare { get; }

        public string Name { get; }
        public string Text { get; }

        public RealEstateProperty(OwnershipType ownType, RealEstateType propType, Country country, decimal? area, string name, string share = "")
        {
            this.OwnershipType = ownType;
            this.PropertyType = propType;
            this.Country = country;
            this.Area = area;
            this.Name = name;
            this.OwnedShare = share;
        }

        public XElement ToXml()
        {
            var xOwnType = new XElement("ownershipType");
            if (OwnershipType == OwnershipType.NotAnOwner)
            {
                xOwnType.Add(XmlHelpers.Nil());
            }
            else
            {
                xOwnType.Value = ((int)OwnershipType).ToString();
            }

            var xPart = new XElement("ownershipPart");

            if (OwnershipType == OwnershipType.Shared)
            {
                if (String.IsNullOrWhiteSpace(OwnedShare))
                {
                    xPart.Add(XmlHelpers.Nil());
                }
                else if (OwnedShare == "½")
                {
                    xPart.Value = (0.5).ToString();
                }
                else if (OwnedShare.Contains("/"))
                {
                    var parts = OwnedShare.Split(new char[] { '/', ' ' });
                    var num = Decimal.Parse(parts[0]);
                    var den = Decimal.Parse(parts[1]);
                    // Убираем ненужные нули в хвосте и, при необходимости, десятичный разделитель
                    xPart.Value = (num / den).ToString().TrimEnd('0').TrimEnd('.');
                }
                else
                {
                    decimal factor = 1.0M;
                    if (OwnedShare.EndsWith("%")) { factor = 0.01M; }
                    string shareStr = OwnedShare.TrimEnd('%');
                    decimal share = Decimal.Parse(shareStr, RussianCulture) * factor;
                    xPart.Value = share.ToString();
                }
            }
            else
            {
                xPart.Add(XmlHelpers.Nil());
            }

            var xArea = new XElement("square");
            if (Area.HasValue)
            {
                xArea.Value = Area.Value.ToString(DefaultCulture);
            }
            else
            {
                xArea.Add(XmlHelpers.Nil());
            }

            var xCountry = new XElement("country");
            if (Country == Country.Undefined)
            {
                xCountry.Add(XmlHelpers.Nil());
            }
            else
            {
                xCountry.Value = ((int)Country).ToString();
            }

            var xName = new XElement("realtyName", Name);

            var res = new XElement("realty",
                        new XElement("realtyType", OwnershipType == OwnershipType.NotAnOwner ? "2" : "1"),
                        new XElement("objectType", (int)ConvertToPluginFriendlyType(PropertyType)),
                        xOwnType,
                        xPart,
                        xArea,
                        xCountry,
                        xName);

            return res;
        }

        private static RealEstateType ConvertToPluginFriendlyType(RealEstateType propertyType)
        {
            switch (propertyType)
            {
                case RealEstateType.Apartment: return RealEstateType.Apartment;
                case RealEstateType.Building: return RealEstateType.Other;
                case RealEstateType.Dacha: return RealEstateType.Dacha;
                case RealEstateType.DachaBuilding: return RealEstateType.Dacha;
                case RealEstateType.DachaHouse: return RealEstateType.Dacha;
                case RealEstateType.Garage: return RealEstateType.Garage;
                case RealEstateType.GardenPlot: return RealEstateType.PlotOfLand;
                case RealEstateType.HabitableBuilding: return RealEstateType.HabitableHouse;
                case RealEstateType.HabitableHouse: return RealEstateType.HabitableHouse;
                case RealEstateType.HabitableSpace: return RealEstateType.Apartment;
                case RealEstateType.House: return RealEstateType.Other;
                case RealEstateType.IndustrialPlot: return RealEstateType.Other;
                case RealEstateType.Other: return RealEstateType.Other;
                case RealEstateType.ParkingSpace: return RealEstateType.Garage;
                case RealEstateType.PlotOfLand: return RealEstateType.PlotOfLand;
                case RealEstateType.Room: return RealEstateType.Apartment;
                case RealEstateType.Rooms: return RealEstateType.Apartment;
                case RealEstateType.Undefined: return RealEstateType.Undefined;
                case RealEstateType.UnfinishedBuilding: return RealEstateType.Other;
                default: throw new ArgumentOutOfRangeException("Unexpected real estate type:" + propertyType.ToString());
            }
        }
    }
}
