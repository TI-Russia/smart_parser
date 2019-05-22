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
                "водный транспорт:",
                "иные транспортные средства:",
                "воздушный транспорт:",
                "сельскохозяйственная техника:",
                "автомобили грузовые:",
                "легковой автомобиль",
                "а/м легковой",
                "а/м"
        };

        private static Regex VehicleTypeRegex = new Regex("(" + string.Join("|", VehicleTypeDict) + ")", RegexOptions.IgnoreCase);
        private static char[] VehicleSeparators = new char[] { ',', ';' };
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
            string multientryType = "";
            foreach (var entry in entries)
            {
                var ve = new VehicleEntry()
                {
                    Count = 1,
                    Type =  multientryType.IsNullOrWhiteSpace() ? "" : multientryType,
                    Model = ""
                };

                var tokens = entry.Split(WhitespaceSeparator, StringSplitOptions.RemoveEmptyEntries);
                foreach (var token in tokens)
                { 
                    if (token.All(Char.IsDigit))
                    {
                        ve.Count = Int32.Parse(token);
                    }
                    else if (IsVehicleType(token))
                    {
                        if (token.EndsWith(MultientryInfix))
                        {
                            ve.Type = multientryType = token.Replace(MultientryInfix, "");
                        }
                        else
                        {
                            ve.Type = token;                                
                        }
                    }
                    else
                    {
                        ve.Model += token + " ";
                    }
                }

                if (ve.Type.IsNullOrWhiteSpace()) { ve.Type = multientryType; }
                ve.Model = ve.Model.Trim();

                res.AddRange(ve.GetVehicles());
            }

            //var matchType = VehicleTypeRegex.Match(str);
            //if (matchType.Success)
            //{
            //    int last_end = -1;
            //    string last_type = null;
            //    string vechicleItemStr = null;
            //    string[] items = null;
            //    foreach (Match itemMatch in VehicleTypeRegex.Matches(str))
            //    {
            //        int begin = itemMatch.Index;
            //        int end = itemMatch.Index + itemMatch.Length;
            //        if (last_end > 0)
            //        {
            //            vechicleItemStr = str.Substring(last_end, begin - last_end);
            //            items = vechicleItemStr.Split(',');
            //            foreach (var item in items)
            //            {
            //                res.Add(new Vehicle(item.Trim(), last_type));
            //            }
            //        }
            //        last_end = end;
            //        last_type = itemMatch.Value.TrimEnd(':', '\n', ' ');
            //    }
            //    vechicleItemStr = str.Substring(last_end);
            //    items = vechicleItemStr.Split(',');
            //    foreach (var item in items)
            //    {
            //        res.Add(new Vehicle(item.Trim(), last_type));
            //    }

            //    return res;
            //}

            //var match = Regex.Match(str, @".+:(.+,.+)");
            //if (match.Success)
            //{
            //    if (res != null)
            //    {
            //        res.AddRange(match.Groups[1].ToString().Split(',').Select(x => new Vehicle(x.Trim())));
            //    }
            //}
            //else
            //{
            //    res.Add(new Vehicle(str));
            //}

            return res;
        }

        private static bool IsVehicleType(string str)
        {
            return VehicleTypeRegex.IsMatch(str);
        }
    }
}
