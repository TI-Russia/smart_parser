using Parser.Lib;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    public class DataHelper
    {
        static public string NormalizeName(string name)
        {
            return String.Join(" ", name.Split(new char[] { ' ' }, StringSplitOptions.RemoveEmptyEntries));
        }
        static public bool IsPublicServantInfo(string nameOrRelativeType)
        {
            if (ParseRelationType(nameOrRelativeType, false) != RelationType.Error)
            {
                return false;
            }
            return true;
        }

        static public bool IsRelativeInfo(string relationshipStr, string occupationStr)
        {
            if (ParseRelationType(relationshipStr, false) != RelationType.Error)
                return true;

            return (!relationshipStr.IsNullOrWhiteSpace()
                    && (!relationshipStr.Contains("фамилия"))
                    && (!relationshipStr.Contains("фио"))
                    && occupationStr.Length <= 1);
        }


        public static RelationType ParseRelationType(string strRel, bool throwException = true)
        {
            switch (strRel.ToLower().Replace(" ", "").Replace("-", "").Replace("\n", "").Trim().RemoveStupidTranslit())
            {
                case "супруг": return RelationType.Spouse;
                case "супруг(супруга)": return RelationType.Spouse;
                case "супруга(супруг)": return RelationType.Spouse;
                case "суруга": return RelationType.Spouse;
                case "супруга": return RelationType.Spouse;
                case "несовершеннолетняядочь": return RelationType.Child;
                case "несовершеннолетнийсын": return RelationType.Child;
                case "несовершеннолетнийребенок": return RelationType.Child;
                case "несовершенолетнийребенок": return RelationType.Child;
                case "дочь": return RelationType.Child;
                case "дочьсупроги": return RelationType.Child;
                case "дочьсупруги": return RelationType.Child;
                case "сынсупруги": return RelationType.Child;
                case "сын": return RelationType.Child;
                case "падчерица": return RelationType.Child;
                case "сынжены": return RelationType.Child;
                case "дочьжены": return RelationType.Child;
                case "несовершеннолетнийребёнок": return RelationType.Child;
                case "племяницасупруги": return RelationType.Spouse;
                case "подопечный": return RelationType.Spouse;
                case "ребёнок": return RelationType.Child;
                case "ребенок": return RelationType.Child;
                default:
                    if (throwException)
                    {
                        throw new ArgumentOutOfRangeException(strRel, $"Неизвестный тип родственника: {strRel}");
                    }
                    return RelationType.Error;
            }
        }
        
        public static bool IsEmptyValue(string s)
        {
            if (s == null) return true;
            s = s.Trim();
            return String.IsNullOrWhiteSpace(s)
                || s == "-"
                || s == "–"
                || s == "_"
                || s == "нет"
                || s == "не имеет";
        }

        public static decimal? ParseDeclaredIncome(string strIncome)
        {
            Decimal result;
            if (IsEmptyValue(strIncome))
                return null;
            else
            {
                try
                {
                    Regex regex = new Regex("([ ,]+[а-яА-Я])|(\\()", RegexOptions.Compiled);
                    var matches = regex.Matches(strIncome);
                    if (matches.Count > 0)
                    {
                        result = strIncome.Substring(0, matches[0].Index).ParseDecimalValue();
                    }
                    else
                    {
                        result = strIncome.ParseDecimalValue();
                    }
                }
                catch (Exception)
                {
                    return null; 
                }

            }

            return Decimal.Round(result, 2);

        }
        public static string ParseDataSources(string src)
        {
            if (IsEmptyValue(src)) return null;
            else return src;
        }

        public static RealEstateType TryParseRealEstateType(string strType)
        {
            string key = strType.ToLower().RemoveStupidTranslit()
                                          .Trim('\"')
                                          .Replace('\n', ' ')
                                          .Replace(';', ' ')
                                          .Replace("не имеет", "")
                                          .Replace("   ", " ")
                                          .Replace("  ", " ")
                                          .Trim();

            RealEstateType type = DeclaratorApiPatterns.TryParseRealEstateType(key);
            return type;
        }

        public static OwnershipType TryParseOwnershipType(string strOwn, OwnershipType defaultType = OwnershipType.None)
        {
            string str = strOwn.ToLower().Trim();
            if (IsEmptyValue(str))
                return defaultType; // OwnershipType.InUse;

            OwnershipType resultWholeString = DeclaratorApiPatterns.TryParseOwnershipType(str);
            if (resultWholeString != OwnershipType.None)
            {
                return resultWholeString;
            }

            //var parts = Regex.Split(str, "[ ,]+");
            var parts = Regex.Split(str, "[ /0-9,\\(\\)]+");

            OwnershipType result = defaultType; // OwnershipType.None;
            foreach (var s in parts)
            {
                OwnershipType res = DeclaratorApiPatterns.TryParseOwnershipType(s);
                if (res != OwnershipType.None)
                {
                    result = res;
                }
            }
            if (result != OwnershipType.None)
            {
                return result;
            }
            return defaultType;
        }

        /*
         *  "квартира           (безвозмездное, бессрочное пользование)"
         *  
         *  "Квартира долевая , 2/3"
         *  
            квартира
            (совместная)  
         */
        static public Tuple<RealEstateType, OwnershipType, string> ParseCombinedRealEstateColumn(string strPropInfo, OwnershipType defaultOwnershipType = OwnershipType.Ownership)
        {
            string share = "1";
            // слово до запятой или до скобки
            var match = Regex.Match(strPropInfo, "[,(]+");
            string realEstateStr = strPropInfo;
            string rest = "";
            string sep = "";
            if (match.Success)
            {
                realEstateStr = strPropInfo.Substring(0, match.Index);
                rest = strPropInfo.Substring(match.Index + 1);
                sep = strPropInfo.Substring(match.Index, 1);
            }

            RealEstateType realEstateType = TryParseRealEstateType(realEstateStr);
            OwnershipType ownershipType = TryParseOwnershipType(realEstateStr);
            share = ParseOwnershipShare(rest, ownershipType);
            if (rest != "")
            {
                OwnershipType t = TryParseOwnershipType(rest);
                if (t != OwnershipType.None)
                {
                    ownershipType = t; 
                }
            }
            if (ownershipType == OwnershipType.None)
            {
                ownershipType = defaultOwnershipType;
            }
            return Tuple.Create(realEstateType, ownershipType, share);
        }

        public static string ParseOwnershipShare(string strOwn, OwnershipType ownType)
        {
            var match = Regex.Match(strOwn, "[½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅐⅛⅜⅝⅞⅑⅒]");
            if (match.Success)
            {
                return match.Value; // vulgar fractions
            }

            match = Regex.Match(strOwn, "\\d+/\\d+");
            if (match.Success)
            {
                return match.Value; // "1/3", "2/5"
            }
            match = Regex.Match(strOwn, "0[\\.,]\\d+");
            if (match.Success)
            {
                return match.Value; // "0.5", "0,7"
            }
            return "";
        }

        private static readonly string[] SquareSeparators = new string[] { "\n", " " };

        public static decimal? ParseSquare(string strSquares)
        {
            if (Regex.Match(strSquares, "[а-я]+", RegexOptions.IgnoreCase).Success)
                return null;

            decimal? area = null;
            // Non-breaking space or breaking space can be between digits like "1 680,0"
            var match = Regex.Match(strSquares, "\\d[\\d\u00A0 ]*([,.]\\d+)?"); 
            if (match.Success)
            {

                Decimal d = match.Value.ParseDecimalValue();
                area = Decimal.Round(d, 2);
            }
            return area;
        }
        

        public static List<decimal?> ParseSquares(string strSquares)
        {
            var res = new List<decimal?>();
            foreach (var str in strSquares.Split(SquareSeparators, StringSplitOptions.RemoveEmptyEntries))
            {
                if (str.Contains("м")) // м. п.м, и т.д.
                {
                    continue;
                }

                decimal? area;
                var match =  Regex.Match(str, "(\\d+)/(\\d+)");
                if (match.Success)
                {
                    string d1 = match.Groups[1].Value;
                    string d2 = match.Groups[2].Value;
                    area = d1.ParseDecimalValue() / d2.ParseDecimalValue();
                }
                else if (Regex.Match(str, "[а-я]+").Success)
                {
                    area = null;
                }
                else if (IsEmptyValue(str))
                {
                    area = null;
                }
                else
                {
                    try
                    { 
                        area = str.ParseDecimalValue();
                    }
                    catch 
                    {
                        area = null;
                    }
                }

                res.Add(area);
            }

            return res;
        }

        private static readonly string[] CountrySeparators = new string[] { "\n" };

        public static Country TryParseCountry(string strCountry)
        {
            if (IsEmptyValue(strCountry))
            {
                return Country.None;
            }
            switch (strCountry.Trim().ToLower())
            {
                case "беларусь": return Country.Belarus;
                case "республика беларусь": return Country.Belarus;
                case "белоруссия": return Country.Belarus;
                case "венгрия": return Country.Hungary;
                case "грузия": return Country.Georgia;
                case "казахстан": return Country.Kazakhstan;
                case "российская федерация": return Country.Russia;
                case "россии": return Country.Russia;
                case "россия": return Country.Russia;
                case "россия-": return Country.Russia;
                case "сша": return Country.Usa;
                case "таиланд": return Country.Thailand;
                case "украина": return Country.Ukraine;
                case "болгария": return Country.Bulgaria;
                case "латвия": return Country.Latvia;
                case "узбекистан": return Country.Uzbekistan;
                case "армения": return Country.Armenia;
                case "турция": return Country.Turkey;
                case "испания": return Country.Spain;
                case "эстония": return Country.Estonia;
                case "монголия": return Country.Mongolia;
                case "таджикистан": return Country.Tajikistan;
                case "чехия": return Country.CzechRepublic;
                case "киргизия": return Country.Kyrgyzstan;
                case "финляндия": return Country.Finland;
                case "франция": return Country.France;
                case "туркмения": return Country.Turkmenistan;
                case "черногория": return Country.Montenegro;
                case "ukraine": return Country.Ukraine;
                case "мексика": return Country.Mexico;
                case "абхазия": return Country.Abkhazia;
                case "южная осетия": return Country.SouthOssetia;
                //default:
            }
            return Country.Error;//throw new SmartParserException("Wrong country name: " + strCountry);
        }

        static public bool ParseVehicle(string vechicleString, List<Vehicle> vehicles)
        {
            vehicles.Clear();
            string[] vehicleTypeDict = {
                @"автомобил. легков..[:|\n ]",
                "мототранспортные средства:",
                "водный транспорт:",
                "иные транспортные средства:",
                "воздушный транспорт:",
                "сельскохозяйственная техника:",
                "автомобили грузовые:",
                "легковой автомобиль",
                "а/м легковой",
                "а/м",
                "легковой прицеп",
                "легковой"
            };
            vechicleString = vechicleString.Trim();
            var vehicleTypeRegex = new Regex("(" + string.Join("|", vehicleTypeDict) + ")", RegexOptions.IgnoreCase);
            string normalVehicleStr = vechicleString.ToLower().Trim();
            if (IsEmptyValue(normalVehicleStr))
            {
                return false;
            }

            var matchType = vehicleTypeRegex.Match(vechicleString);
            if (matchType.Success)
            {
                int last_end = -1;
                string last_type = null;
                string vechicleItemStr = null;
                string[] items = null;
                foreach (Match itemMatch in vehicleTypeRegex.Matches(vechicleString))
                {
                    int begin = itemMatch.Index;
                    int end = itemMatch.Index + itemMatch.Length;
                    if (last_end > 0)
                    {
                        vechicleItemStr = vechicleString.Substring(last_end, begin - last_end);
                        items = vechicleItemStr.Split(',');
                        foreach (var item in items)
                        {
                            vehicles.Add(new Vehicle(item.Trim(), last_type));
                        }
                    }
                    last_end = end;
                    last_type = itemMatch.Value.TrimEnd(':', '\n', ' ');
                }
                vechicleItemStr = vechicleString.Substring(last_end);
                items = vechicleItemStr.Split(',');
                foreach (var item in items)
                {
                    if (last_type == "легковой") last_type = "Автомобиль легковой";
                    vehicles.Add(new Vehicle(item.Trim(), last_type));
                }

                return true;
            }

            var match = Regex.Match(vechicleString, @".+:(.+,.+)");
            if (match.Success)
            {
                if (vehicles != null)
                {
                    vehicles.AddRange(match.Groups[1].ToString().Split(',').Select(x => new Vehicle(x.Trim())));
                }
            }
            else
            {
                vehicles.Add(new Vehicle(vechicleString));
            }
            return true;
        }
    }
}
