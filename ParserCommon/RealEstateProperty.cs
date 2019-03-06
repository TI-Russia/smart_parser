using System;
using System.Globalization;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class RealEstateProperty
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        public OwnershipType OwnershipType { set;  get; }
        public RealEstateType PropertyType { set; get; }

        public Country Country { set; get; }
        public decimal? Area { set; get; }
        public string OwnedShare { set; get; }

        public string square_raw { set; get; }
        public string share_amount_raw { set; get; }
        public string country_raw { set; get; }
        public string type_raw { set; get; }
        public string own_type_raw { set; get; }

        public string Name { set; get; }
        public string Text { set; get; }

        public RealEstateProperty()
        {}

        public RealEstateProperty(OwnershipType ownType, RealEstateType propType, Country country, decimal? area, string name, string share = "")
        {
            this.OwnershipType = ownType;
            this.PropertyType = propType;
            this.Country = country;
            this.Area = area;
            this.Name = name;
            this.OwnedShare = share;
        }

        /*
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
                //case RealEstateType.GardenPlot: return RealEstateType.PlotOfLand;
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
                //case RealEstateType.Undefined: return RealEstateType.Undefined;
                case RealEstateType.UnfinishedBuilding: return RealEstateType.Other;
                default: throw new ArgumentOutOfRangeException("Unexpected real estate type:" + propertyType.ToString());
            }
        }
        */
    }
}
