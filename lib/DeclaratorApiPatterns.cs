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
         realestatetype - гараж, квартира и т.д.
         */
        static Dictionary<string, string> realestatetypeDict = new Dictionary<string, string>();
        static List<string> realestatetypeRegex = new List<string>();

        static Dictionary<string, string> countryDict = new Dictionary<string, string>();
        /*
        owntype:
            В собственности, в пользовании, наем (аренда)

        */
        static Dictionary<string, string> owntypeDict = new Dictionary<string, string>();
        static List<string> owntypeRegex = new List<string>();

        /*
        sharetype:
            Долевая, совместная, индивидуальная
        */
        static Dictionary<string, string> sharetypeDict = new Dictionary<string, string>();
        static List<string> sharetypeRegex = new List<string>();

        static DeclaratorApiPatterns()
        {
            foreach (Result pattern in Patterns.results)
            {
                switch (pattern.type)
                {
                    case "realestatetype":
                        if (pattern.is_regex)
                            realestatetypeRegex.Add(pattern.value);
                        else
                            realestatetypeDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "country":
                        if (pattern.is_regex)
                            throw new Exception("Regex not supproted");
                        countryDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "owntype":
                        if (pattern.is_regex)
                            owntypeRegex.Add(pattern.value);
                        else 
                            owntypeDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "sharetype":
                        if (pattern.is_regex)
                            sharetypeRegex.Add(pattern.value);
                        else
                            sharetypeDict[pattern.data.ToLower()] = pattern.value;
                        break;
                    case "carbrand":
                    case "vehicletype":
                        break;
                    default:
                        throw new Exception("unknown pattern.type " + pattern.type);
                }
            }
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
                { "Жилой дом", RealEstateType.House},
                { "Квартира", RealEstateType.Apartment },
                { "Иное", RealEstateType.Other },
                { "Гараж", RealEstateType.Garage },
                { "Земельный участок", RealEstateType.PlotOfLand },
                { "Дача", RealEstateType.Dacha }
            };


        static Dictionary<string, OwnershipType> OwnershipTypeMap =
            new Dictionary<string, OwnershipType>()
            {
                { "Наём (аренда)", OwnershipType.Lease}, 
                { "В пользовании", OwnershipType.InUse},
                { "Служебное жилье", OwnershipType.Corp},
                { "В собственности", OwnershipType.Ownership },
                { "Фактическое предоставление", OwnershipType.ProvisionForUse}
            };

        public static RealEstateType ParseRealEstateType(string text)
        {
            string normalized = NormalizeText(text);
            string value = GetValue(normalized, "realestatetype");

            if (value.IsNullOrWhiteSpace())
            {
                throw new UnknownRealEstateTypeException(normalized);
            }

            return RealEstateTypeMap[value];
        }

        public static OwnershipType ParseOwnershipType(string text)
        {
            string normalized = NormalizeText(text);
            string value = GetValue(normalized, "owntype");
            if (value.IsNullOrWhiteSpace())
            {
                throw new UnknownRealEstateTypeException(normalized);
            }
            return OwnershipTypeMap[value];
        }

    }
}

