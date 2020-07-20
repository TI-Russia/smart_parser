using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Text.RegularExpressions;
using System.Globalization;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;
using System.Reflection;

namespace Smart.Parser.Lib
{
    public class DataHelper
    {
        static Regex CountryRegexp;
        static Regex SquareAndCountryRegexp;
        static Regex SquareRegexp;
        static DataHelper()
        {
            var countryList = ReadCountryList();
            string anyCountry = "(" + string.Join(")|(", countryList.ToArray()) + ")";
            CountryRegexp = new Regex(anyCountry, RegexOptions.IgnoreCase);

            // Non-breaking space or breaking space can be between digits like "1 680,0"
            string squareRegexpStr = "(\\d[\\d\u00A0 ]*(?:[,.]\\d+)?)";
            SquareAndCountryRegexp = new Regex(squareRegexpStr + @"\s+(" + anyCountry + ")", RegexOptions.IgnoreCase);
            SquareRegexp = new Regex(squareRegexpStr, RegexOptions.IgnoreCase);
        }

        static public List<string> ParseCountryList(string s)   {
            s = s.Trim();
            var countries = new List<string>();
            while (s.Length > 0)
            {
                var match = CountryRegexp.Match(s);
                if (match.Success && match.Index == 0 && match.Length > 0)
                {
                    countries.Add(match.Value);
                }
                else
                {
                    return new List<string>();
                }
                s = s.Substring(match.Length).Trim();
            }
            return countries;
        }

        static List<string> ReadCountryList() {
            // taken from https://github.com/umpirsky/country-list

            var countries = new List<string>();
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.countries_in_russian.json"))
            {
                using (var file = new System.IO.StreamReader(stream))
                {
                    string jsonStr = file.ReadToEnd();
                    var country2code = JsonConvert.DeserializeObject<Dictionary<string, string>>(jsonStr);
                    foreach (var s in country2code.Keys)
                    {
                        countries.Add(s.ToLower());
                    }
                }
            }
            return countries;
        }
        static public bool IsPublicServantInfo(string nameOrRelativeType)
        {
            if (IsEmptyValue(nameOrRelativeType)) return false;

            if (ParseRelationType(nameOrRelativeType, false) != RelationType.Error)
            {
                return false;
            }
            return true;
        }

        static public bool IsRelativeInfo(string relationshipStr)
        {
            return ParseRelationType(relationshipStr, false) != RelationType.Error;
        }


        public static RelationType ParseRelationType(string strRel, bool throwException = true)
        {
            string clean = strRel.ToLower()
                .Replace(" ", "")
                .Replace(":", "")
                .Replace("-", "")
                .Replace("\n", "")
                .Replace("ё", "е")
                .Replace(".", "").Trim().RemoveStupidTranslit().ToLower();
            switch (clean)
            {
                case "супруг": return RelationType.Spouse;
                case "упруга": return RelationType.Spouse;
                case "супуг": return RelationType.Spouse;
                case "супруг(супруга)": return RelationType.Spouse;
                case "супруга(супруг)": return RelationType.Spouse;
                case "суруга": return RelationType.Spouse;
                case "спруга": return RelationType.Spouse;
                case "супруа": return RelationType.Spouse;
                case "супуга": return RelationType.Spouse;
                case "супруга": return RelationType.Spouse;
                case "супруг(а)": return RelationType.Spouse;
                case "супругнет": return RelationType.Spouse;
                case "муж": return RelationType.Spouse;
                case "жена": return RelationType.Spouse;
                case "жены": return RelationType.Spouse;
                case "подопечный": return RelationType.Spouse;
                case "супруги": return RelationType.Spouse;
                case "суапруга": return RelationType.Spouse;
                case "сурпуга": return RelationType.Spouse;
                case "спруг": return RelationType.Spouse;
                case "супргуа": return RelationType.Spouse;
                case "супруна": return RelationType.Spouse;

                case "несовершенно": return RelationType.Child;
                case "несовершеннолетняядочь": return RelationType.Child;
                case "несовершеннолетнийсын": return RelationType.Child;
                case "несовершеннолетниедети": return RelationType.Child;
                case "несовершеннолетнийребенок": return RelationType.Child;
                case "несовершеннолетнийребенокнет": return RelationType.Child;
                case "несовершенолетнийребенок": return RelationType.Child;
                case "несовершеннолетнийребенок(дочь)": return RelationType.Child;
                case "несовершеннолетнийребенок(сын)": return RelationType.Child;
                case "несовершеннолетниеребенок": return RelationType.Child;
                case "несовершеннолребенок": return RelationType.Child;
                case "н/ребенок": return RelationType.Child;
                case "дочь": return RelationType.Child;
                case "дрчь": return RelationType.Child;
                case "дочери": return RelationType.Child;
                case "дочьсупроги": return RelationType.Child;
                case "дочьсупруги": return RelationType.Child;
                case "сынсупруги": return RelationType.Child;
                case "сын": return RelationType.Child;
                case "сына": return RelationType.Child;
                case "сынжены(находитсянаиждивении)": return RelationType.Child;
                case "пасынок": return RelationType.Child;
                case "падчерица": return RelationType.Child;
                case "сынжены": return RelationType.Child;
                case "дочьжены": return RelationType.Child;
                case "несовершеннолетнийребёнок": return RelationType.Child;
                case "несовешеннолетнийребенок": return RelationType.Child;
                case "несовершеннолетийребенок": return RelationType.Child;
                case "несовершеннолетний": return RelationType.Child;
                case "несовершеноленийребенок": return RelationType.Child;
                case "нсовершеннолетнийребенок": return RelationType.Child;
                case "совершеннолетнийребенок": return RelationType.Child;
                case "несоверщеннолетнийребенок": return RelationType.Child;
                case "ребёнок": return RelationType.Child;
                case "ребенок": return RelationType.Child;
                case "иждивенец": return RelationType.Child;
                case "опекаемая": return RelationType.Child;
                case "опекаемый": return RelationType.Child;
                case "иждивенц": return RelationType.Child;

                case "племяницасупруги": return RelationType.Other;
                case "мать": return RelationType.Other;
                case "членсемьи": return RelationType.Other;

                default:
                    if (clean.StartsWith("ребенок") || clean.StartsWith("ребёнок") || clean.StartsWith("сын") || clean.StartsWith("дочь") || clean.StartsWith("несовершеннол"))
                        return RelationType.Child;
                    if (clean.StartsWith("супруг"))
                        return RelationType.Spouse;
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
            s = s.Trim().ToLower();
            if (Regex.Match(s, @"^[\s-_]+$").Success)
            {
                return true;
            }
            return String.IsNullOrWhiteSpace(s)
                || s == "-"
                || s == "─"
                || s == "?"
                || s == "- - -"
                || s == "–"
                || s == "_"
                || s == "—"
                || s == "нет"
                || s == "не имеет"
                || s == "не указан"
                || s == "не указано"
                || s == "не работает"
                || s == "отсутствует";
        }

        static decimal ParseRoubles(string val, bool inThousands) {
            val = val.Trim();
            decimal res = val.ParseDecimalValue();
            if (res > 10000000000)
            {
                throw new Exception("income is greater than 10.000.000.000");
            }
            if (res == 0)
            {
                return res;
            }
            if (res > 2000000) // can be included in income charts...
            {
                //"1 039 300 94" -> 1 039 300,94
                Regex subRegex = new Regex(@"([0-9])(\s+)([0-9][0-9])$", RegexOptions.Compiled);
                val = subRegex.Replace(val, "$1,$3");
                res = val.ParseDecimalValue();

            }


            if (!inThousands)
            {
                string processedVal = Regex.Replace(val, @"\s+", "").Trim();
                //no more than two digits after comma, cannot start with 0    
                Regex regex = new Regex("^([1-9][0-9]*)([.,][0-9]{1,2})?$", RegexOptions.Compiled);
                var matches = regex.Matches(processedVal);
                if (matches.Count == 0)
                {
                    throw new Exception(String.Format("bad format in income field {0}", val)); ;
                }
            }
            return res;
            
        }
        public static decimal? ParseDeclaredIncome(string strIncome, bool inThousands)
        {
            Decimal result;
            if (IsEmptyValue(strIncome))
                return null;
            else
            {
                try
                {
                    strIncome = strIncome.Replace("\n", " ");
                    strIncome = new Regex(".*Общая\\s+сумма\\s+доходов:", RegexOptions.Compiled).Replace(strIncome, "");

                    Regex regex = new Regex("([ ,]+[а-яА-Я])|(\\()", RegexOptions.Compiled);
                    var matches = regex.Matches(strIncome);
                    if (matches.Count > 0)
                    {
                        result = ParseRoubles(strIncome.Substring(0, matches[0].Index), inThousands);
                    }
                    else
                    {
                        result = ParseRoubles(strIncome, inThousands);
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

        public static string TryParseRealEstateType(string strType)
        {
            string key = strType.ToLower().RemoveStupidTranslit()
                                          .Trim('\"')
                                          .Replace('\n', ' ')
                                          .Replace(';', ' ')
                                          .Replace("не имеет", "")
                                          .CoalesceWhitespace()
                                          .Trim();

            return key;
        }

        public static Decimal ConvertSquareFromString(string str)
        {
            return  Decimal.Round(str.ParseDecimalValue(), 2);
        }

        static public bool ReadSquareAndCountry(string str, out decimal square, out string country)
        {
            square = 0;
            country = "";
            var match = SquareAndCountryRegexp.Match(str);
            if (!match.Success)
                return false;
            square = ConvertSquareFromString(match.Groups[1].ToString());
            country = match.Groups[2].ToString();
            return true;
        }

        public static decimal? ParseSquare(string strSquares)
        {
            decimal square;
            string dummy;
            if (ReadSquareAndCountry(strSquares, out square, out dummy))
            {
                return square;
            }
            if (Regex.Match(strSquares, "[а-я]+", RegexOptions.IgnoreCase).Success)
                return null;

            var match = SquareRegexp.Match(strSquares);
            if (!match.Success) return null;
            return  Decimal.Round(match.Value.ParseDecimalValue(), 2);
        }
        public static bool IsCountryStrict(string str)
        {
            var match = CountryRegexp.Match(str);
            return match.Success;
        }

        public static string ParseCountry(string str)
        {
            decimal dummy;
            string country;
            if (ReadSquareAndCountry(str, out dummy, out country))
            {
                return country;
            }
            return str;
        }
        static public bool ParseDocumentFileName(string filename, out int? documentfile_id, out string archive_file)
        {
            documentfile_id = null;
            archive_file = null;
            string filePath = Path.GetFullPath(filename);
            string dirName = new DirectoryInfo(Path.GetDirectoryName(filePath)).Name;
            int dirId;
            bool dirParseRes = Int32.TryParse(dirName, out dirId);
            // dirty hack
            if (dirParseRes && (dirId > 2020 || dirId < 2000))
            {
                documentfile_id = Int32.Parse(dirName);
                archive_file = Path.GetFileName(filename);
                return true;
            }
            else
            {
                int val;
                bool res = Int32.TryParse(Path.GetFileNameWithoutExtension(filename), out val);
                if (res) { documentfile_id = val; }
                return res;
            }
        }
    }
}
