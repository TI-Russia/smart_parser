using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace TI.Declarator.ParserCommon
{
    public static class ParserHelpers
    {
        private static string[] VehicleTypeDict =
        {
                @"автомобил. легков..[:|\n ]",                
                "мототранспортные средства:",
                "мотоцикл.[:|\n ]",
                "водный транспорт:",
                "лодка",
                "иные транспортные средства:",
                "воздушный транспорт:",
                "сельскохозяйственная техника:",
                "автомобили грузовые:",
                "легковой автомобиль",
                "а/м легковой",
                "а/м",
                "водный транспорт",
                "автоприцеп",
                "мототран-спортное средство",
                "мотовездеход"
        };

        private static Regex VehicleTypeRegex = new Regex("(" + string.Join("|", VehicleTypeDict) + ")", RegexOptions.IgnoreCase);
        private static string[] VehicleSeparators = new string[] { "\n\n", ",\n", ", ", ";" };
        private static char[] WhitespaceSeparator = new char[] { ' ' };
        private static string MultientryInfix = ":";
        public static IEnumerable<Vehicle> ExtractVehicles(string str)
        {
            var res = new List<Vehicle>();

            str = str.Trim();
            string normalVehicleStr = str.ToLower();
            if (String.IsNullOrEmpty(normalVehicleStr) ||
                normalVehicleStr == "не имеет" ||
                normalVehicleStr == "-" ||
                normalVehicleStr == "_")
            {
                return res;
            }

            var entries = str.Split(VehicleSeparators, StringSplitOptions.RemoveEmptyEntries);
            string multientryType = null;
            foreach (var entry in entries.Select(e => e.CleanWhitespace().CoalesceWhitespace()))
            {
                string type = ExtractVehicleType(entry);

                string entrySansType = entry;
                if (!type.IsNullOrWhiteSpace())
                {
                    entrySansType = entry.Replace(type, "");
                    type = multientryType = type.Replace(MultientryInfix, "");
                }                                

                var ve = new VehicleEntry()
                {
                    Count = 1,
                    Type = type.IsNullOrWhiteSpace() ? multientryType : type,
                    Model = ""
                };

                var tokens = entrySansType.Split(WhitespaceSeparator, StringSplitOptions.RemoveEmptyEntries);

                if (tokens.Count() > 0)
                {
                    string headToken = tokens[0];
                    if (headToken.All(Char.IsDigit))
                    {
                        ve.Model = entrySansType.ReplaceFirst(headToken, "");
                    }
                    else
                    {
                        ve.Model = entrySansType;
                    }

                    ve.Model = ve.Model.Replace(MultientryInfix, " ").CoalesceWhitespace().Trim();
                }
                // No model info given; store vehicle type instead
                else
                {
                    ve.Model = ve.Type;
                }


                res.AddRange(ve.GetVehicles());
            }

            return res;
        }

        private static string ExtractVehicleType(string str)
        {
            if (VehicleTypeRegex.IsMatch(str))
            {
                return VehicleTypeRegex.Match(str).Value;
            }
            else
            {
                return null;
            }            
        }
    }
}
