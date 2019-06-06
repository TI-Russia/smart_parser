using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;


namespace Smart.Parser.Lib
{

    public class Rootobject
    {
        public Result[] results { get; set; }
    }

    public class Result 
    {
        public string data { get; set; }
        public int id { get; set; }
        public bool is_case { get; set; }
        public bool is_regex { get; set; }
        public string type { get; set; }
        public string value { get; set; }
    }

    public class DeclaratorApiPatterns
    {
        /*
         * API that return 
         */
        /*
         realestatetype - гараж, квартира и т.д.
         */
        static Dictionary<string, RealEstateType> realestatetypeDict = new Dictionary<string, RealEstateType>();
        //static Regex realestatetypeRegex;
        //static string realestatetypeRegexString;
        static Dictionary<RealEstateType, Regex> RealEstateTypeRegexes = new Dictionary<RealEstateType, Regex>();
        static SymSpell RealEstateTypeSpellDict = new SymSpell(10000, 2);

        static Dictionary<string, string> countryDict = new Dictionary<string, string>();
        /*
        owntype:
            В собственности, в пользовании, наем (аренда)

        */
        static Dictionary<string, string> owntypeDict = new Dictionary<string, string>();
        static List<string> owntypeRegex = new List<string>();

        static Dictionary<T1, T2> ReverseDict<T1, T2>(Dictionary<T2, T1> src)
        {
            return src.ToList().ToDictionary<KeyValuePair<T2, T1>, T1, T2>(obj => obj.Value, obj => obj.Key);
        }

        static DeclaratorApiPatterns()
        {
            Dictionary<RealEstateType, List<string>>  realestatetypeRegexList = new Dictionary<RealEstateType, List<string>>();
            foreach (Result pattern in Patterns.results)
            {
                switch (pattern.type)
                {
                    case "realestatetype":
                        RealEstateType value = RealEstateTypeMap[pattern.value];
                        if (pattern.is_regex)
                        {
                            if (!realestatetypeRegexList.ContainsKey(value))
                            {
                                realestatetypeRegexList[value] = new List<string>() { pattern.data };
                            }
                            else
                            {
                                realestatetypeRegexList[value].Add(pattern.data);
                            }

                            //System.Diagnostics.Debug.WriteLine(String.Format("{0} - {1}", pattern.data, pattern.value));
                        }
                        else
                        {
                            realestatetypeDict[pattern.data.ToLower()] = value;
                        }
                        break;
                    case "owntype":
                        if (pattern.is_regex)
                            owntypeRegex.Add(pattern.value);
                        else
                            owntypeDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "country":
                        if (pattern.is_regex)
                            throw new Exception("Regex not supproted");
                        countryDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "carbrand":
                    case "vehicletype":
                    case "relative":
                        break;
                    default:
                        throw new Exception("unknown pattern.type " + pattern.type);
                }
            }

            // build realestate regex
            List<String> allTypes;
            foreach (var pair in realestatetypeRegexList)
            {
                string realestatetypeRegexString = "(" + String.Join("|", pair.Value) + ")";
                RealEstateTypeRegexes[pair.Key] = new Regex(realestatetypeRegexString, RegexOptions.IgnoreCase | RegexOptions.Compiled);
                foreach (var s in pair.Value)
                { 
                    var simplified = s.Replace("\\b", "").Replace("\\s", " ").ToLower();
                    RealEstateTypeSpellDict.CreateDictionaryEntry(simplified, (int)pair.Key);

                }
            }

            BuildCustomDicts();
        }

        static void BuildCustomDicts()
        {
            //realestatetypeDict["совместная"] = RealEstateType.S"Совместная собственность";
            string[] countries =
            {
                "абхазия",
                "великобритания",
                "туркменистан",
                "белоруссия",
                "армения",
                "куба",
                "корея",
                "дания",
                "бельгия",
                "вьетнам",
                "китай",
                "аргентина",
                "япония",
                "черногория",
                "германия",
                "швеция",
                "пакистан",
                "швейцария",
                "таджикистан",
                "испания",
                "бразилия",
                "таиланд",
                "турция",
                "узбекистан",
                "киргизия",
                "беларусь",
                "никарагуа",
                "малайзия",
                "украина",
                "сша",
                "австрия",
                "чехия",
                "латвия",
                "индия",
                "канада",
                "франция",
                "сербия",
                "марокко",
                "нидерланды",
                "норвегия",
                "литва",
                "финляндия",
                "венгрия",
                "казахстан",
                "польша",
                "египет",
                "словакия",
                "болгария",
                "иран",
                "грузия",
                "италия",
                "кипр",
                "мексика"
            };
            foreach (var c in countries)
                countryDict[c] = c;

            countryDict["россия"] = "россия";
            countryDict["российская федерация"] = "россия";
            countryDict[""] = "россия";
            countryDict["рф"] = "россия";
            countryDict["республика болгария"] = "болгария";
        }

        static string GetResourceText()
        {
            string result = null;
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.patterns.json"))
            using (var reader = new StreamReader(stream))
            {
                result = reader.ReadToEnd();
            }
            return result;
        }

        static Rootobject patterns = null;
        static Rootobject Patterns
        {
            get
            {
                if (patterns == null)
                    patterns = JsonConvert.DeserializeObject<Rootobject>(GetResourceText());
                return patterns;
            }
        }
        public static string GetValue(string text, string type)
        {
            foreach (Result pattern in Patterns.results.Where(result => result.type == type))
            {
                if (pattern.is_regex)
                {
                    if (Regex.Match(text, pattern.data.ToLower()).Success)
                        return pattern.value.Trim();
                }
                else if (pattern.data.ToLower() == text)
                {
                    return pattern.value.Trim();
                }
            }



            return null;
        }
        static string NormalizeText(string text)
        {
            text = text.ToLower().RemoveStupidTranslit()
                                          .Trim('\"')
                                          .Replace('\n', ' ')
                                          .Replace(';', ' ')
                                          .Trim();

            text = Regex.Replace(text, @"\s{2,}", " ");

            return text;
        }

        static Dictionary<string, RealEstateType> RealEstateTypeMap =
            new Dictionary<string, RealEstateType>()
            {
                { "Жилой дом", RealEstateType.ResidentialHouse},
                { "Квартира", RealEstateType.Apartment },
                { "Иное", RealEstateType.Other },
                { "Гараж", RealEstateType.Garage },
                { "Земельный участок", RealEstateType.PlotOfLand },
                { "Дача", RealEstateType.Dacha },
                { "Линейный объект", RealEstateType.InfrastructureFacility }
            };
        static Dictionary<RealEstateType, string> RealEstateRevMap = ReverseDict(RealEstateTypeMap);

        static Dictionary<string, OwnershipType> OwnershipTypeMap =
            new Dictionary<string, OwnershipType>()
            {
                { "Индивидуальная", OwnershipType.Individual},
                { "Совместная собственность", OwnershipType.Joint},
                { "Долевая собственность", OwnershipType.Shared},
                { "В пользовании", OwnershipType.InUse},
                { "Наём (аренда)", OwnershipType.Lease}, 
                { "Служебное жилье", OwnershipType.ServiceHousing},
                { "В собственности", OwnershipType.Ownership },
                { "Фактическое предоставление", OwnershipType.ProvisionForUse},
                { "Безвозмездное пользование", OwnershipType. InFreeUse }
            };
        static Dictionary<OwnershipType, string> OwnershipRevMap = ReverseDict(OwnershipTypeMap);


        public static RealEstateType TryParseRealEstateType(string text)
        {
            string normalized = NormalizeText(text);

            foreach (var pair in RealEstateTypeRegexes)
            {
                if (pair.Value.IsMatch(normalized))
                    return pair.Key;
            }
            if (text.Count() > 3)
            {    
                foreach (var suggestion in RealEstateTypeSpellDict.Lookup(text.ToLower(), SymSpell.Verbosity.Closest, 1))
                {
                    return (RealEstateType)suggestion.count;
                }
            }

            RealEstateType result = RealEstateType.None;

            realestatetypeDict.TryGetValue(text, out result);

            return result;

        }

        public static RealEstateType ParseRealEstateType(string text)
        {
            RealEstateType type = TryParseRealEstateType(text);
            if (type == RealEstateType.None)
            {
                throw new UnknownRealEstateTypeException(text);
            }
            return type;
        }


        public static string RealEstateTypeToString(RealEstateType real_type)
        {
            try
            {
                return RealEstateRevMap[real_type];
            }
            catch
            {
                throw new UnknownRealEstateTypeException(real_type.ToString());
            }
        }
        public static OwnershipType TryParseOwnershipType(string text)
        {
            string normalized = NormalizeText(text);
            string value = GetValue(normalized, "owntype");
            if (value.IsNullOrWhiteSpace())
            {
                return OwnershipType.None;
            }
            return OwnershipTypeMap[value];
        }

        public static OwnershipType ParseOwnershipType(string text)
        {
            OwnershipType type = TryParseOwnershipType(text);
            if (type == OwnershipType.None)
            {
                throw new UnknownOwnershipTypeException(text);
            }
            return type;
        }

        public static string OwnershipTypeToString(OwnershipType own_type)
        {
            try
            {
                return OwnershipRevMap[own_type];
            }
            catch 
            {
                throw new UnknownOwnershipTypeException(own_type.ToString());
            }
        }

        public static string TryParseCountry(string country)
        {
            if (country.Trim() == "" || country.Trim() == "-")
            {
                return "";
            }

            string normalized = NormalizeText(country);

            string value = null;
            countryDict.TryGetValue(normalized, out value);
            if (value != null)
            { 
                value =  char.ToUpper(value[0]) + value.Substring(1);
            }

            return value; 
        }

        public static string ParseCountry(string text)
        {
            string value = TryParseCountry(text);
            if (value.IsNullOrWhiteSpace())
            {
                throw new UnknownCountryException(text);
            }
            return value;
        }



    }
}

