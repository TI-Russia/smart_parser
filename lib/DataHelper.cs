using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;
using System.Reflection;
using SmartAntlr;

namespace Smart.Parser.Lib
{
    public class DataHelper
    {
        private static readonly Regex SquareRegexp;
        private static readonly AntlrStrictParser SquareAndCountry = new AntlrStrictParser(AntlrStrictParser.StartFromRootEnum.square_and_country);
        private static readonly AntlrCountryListParser CountryListParser = new AntlrCountryListParser();

        static DataHelper()
        {
            // Non-breaking space or breaking space can be between digits like "1 680,0"
            const string squareRegexpStr = "(\\d[\\d\u00A0 ]*(?:[,.]\\d+)?)";
            SquareRegexp = new Regex(squareRegexpStr, RegexOptions.IgnoreCase);
        }

        private static List<string> ReadCountryList()
        {
            // taken from https://github.com/umpirsky/country-list

            var countries = new List<string>();
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.countries_in_russian.json"))
            {
                using var file = new StreamReader(stream);
                var jsonStr = file.ReadToEnd();
                var country2code = JsonConvert.DeserializeObject<Dictionary<string, string>>(jsonStr);
                foreach (var s in country2code.Keys)
                {
                    countries.Add(s.ToLower());
                }
            }

            return countries;
        }

        public static bool IsPublicServantInfo(string nameOrRelativeType)
        {
            if (IsEmptyValue(nameOrRelativeType))
            {
                return false;
            }

            return ParseRelationType(nameOrRelativeType, false) == RelationType.Error;
        }

        public static bool IsRelativeInfo(string relationshipStr) => ParseRelationType(relationshipStr, false) != RelationType.Error;

        private static readonly ISet<string> RelationSpouseStrings = new HashSet<string>()
        {
            "жена", "жены",
            "муж",
            "подопечный",
            "спруг", "спруга", "суапруга", "супргуа", "супргуга", "супруа", "супруг", "супруг(а)", "супруг(супруга)", "супруга",
            "супруга(супруг)", "супруги", "супругнет", "супруна", "супуг", "супуга", "сурпуга", "суруга", "упруга",
        };

        private static readonly ISet<string> RelationChildStrings = new HashSet<string>()
        {
            "дочери", "дочь", "дочьжены", "дочьсупроги", "дочьсупруги", "дрчь",
            "иждивенец", "иждивенц",
            "н/ребенок", "несовершенно", "несовершеннолетийребенок", "несовершеннолетниедети", "несовершеннолетниеребенок",
            "несовершеннолетний", "несовершеннолетнийребенок", "несовершеннолетнийребенок(дочь)", "несовершеннолетнийребенок(сын)",
            "несовершеннолетнийребенокнет", "несовершеннолетнийребёнок", "несовершеннолетнийсын", "несовершеннолетняядочь", "несовершеннолребенок",
            "несовершеноленийребенок", "несовершенолетнийребенок", "несоверщеннолетнийребенок", "несовешеннолетнийребенок", "нсовершеннолетнийребенок",
            "опекаемая", "опекаемый",
            "падчерица", "пасынок",
            "ребенок", "ребёнок", "совершеннолетнийребенок",
            "сын", "сына", "сынжены", "сынжены(находитсянаиждивении)", "сынсупруги",
        };

        private static readonly ISet<string> RelationOtherStrings = new HashSet<string>()
        {
            "племяницасупруги", "мать", "членсемьи",
        };

        public static RelationType ParseRelationType(string strRel, bool throwException = true)
        {
            var clean = strRel
                .ToLower()
                .RemoveCharacters(' ', ':', '-', '\n', '.')
                .Replace('ё', 'е')
                .Trim()
                .RemoveStupidTranslit()
                .ToLower();

            return clean switch
            {
                _ when RelationSpouseStrings.Contains(clean) || clean.StartsWith("супруг")                                                  => RelationType.Spouse,
                _ when RelationChildStrings.Contains(clean) || clean.StartsWithAny("ребенок", "ребёнок", "сын", "дочь", "несовершеннол")    => RelationType.Child,
                _ when RelationOtherStrings.Contains(clean)                                                                                 => RelationType.Other,
                _ => throwException ? throw new ArgumentOutOfRangeException(strRel, $"Неизвестный тип родственника: {strRel}") : RelationType.Error,
            };
        }

        private static readonly ISet<string> EmptyStrings = new HashSet<string>()
        {
            "- - -", "-", "?", "_", "не имеет", "не работает", "не указан", "не указано", "нет", "отсутствует", "–", "—", "─",
        };

        public static bool IsEmptyValue(string s)
        {
            if (string.IsNullOrWhiteSpace(s))
            {
                return true;
            }

            s = s.Trim().ToLowerInvariant();
            return EmptyStrings.Contains(s) || Regex.Match(s, @"^[\s-_]+$").Success;
        }

        private static decimal ParseRoubles(string val, bool inThousands)
        {
            val = val.Trim();
            var hyphenMatch = Regex.Match(val, @"(\d+)-\d\d$");
            if (hyphenMatch.Success)
            {
                //1241300-00, I hope that '00' are cents, so round them (skip)
                val = hyphenMatch.Groups[1].Value;
            }
            var roubleMatch = Regex.Match(val, @"(.+)\s+(руб\.)|(р\.)|(рублей)(рублей)|(рубль)$");
            if (roubleMatch.Success)
            {
                //5 рублей
                val = roubleMatch.Groups[1].Value;
            }
            var res = val.ParseDecimalValue();
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
                // "1 039 300 94" -> 1 039 300,94
                var subRegex = new Regex(@"([0-9])(\s+)([0-9][0-9])$", RegexOptions.Compiled);
                val = subRegex.Replace(val, "$1,$3");
                res = val.ParseDecimalValue();
            }

            if (!inThousands)
            {
                var processedVal = Regex.Replace(val, @"\s+", string.Empty).Trim();
                // no more than two digits after comma, cannot start with 0
                var regex = new Regex("^([1-9][0-9]*)([.,][0-9]{1,2})?$", RegexOptions.Compiled);
                var matches = regex.Matches(processedVal);
                if (matches.Count == 0)
                {
                    throw new Exception($"bad format in income field {val}");
                }
            }

            return res;
        }

        public static decimal? ParseDeclaredIncome(string strIncome, bool inThousands)
        {
            decimal result;
            if (IsEmptyValue(strIncome))
            {
                return null;
            }
            else
            {
                try
                {
                    strIncome = strIncome.Replace("\n", " ");
                    strIncome = new Regex(".*Общая\\s+сумма\\s+доходов:", RegexOptions.Compiled).Replace(strIncome, string.Empty);

                    var regex = new Regex("([ ,]+[а-яА-Я])|(\\()", RegexOptions.Compiled);
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

            return decimal.Round(result, 2);
        }

        public static string ParseDataSources(string src) => IsEmptyValue(src) ? null : src;

        public static string TryParseRealEstateType(string strType)
        {
            var key = strType.ToLower().RemoveStupidTranslit()
                                          .Trim('\"')
                                          .Replace('\n', ' ')
                                          .Replace(';', ' ')
                                          .Replace("не имеет", string.Empty)
                                          .CoalesceWhitespace()
                                          .Trim();

            return key;
        }

        public static decimal ConvertSquareFromString(string str) => decimal.Round(str.ParseDecimalValue(), 2);

        public static void ReadSquareAndCountry(string str, out decimal square, out string country)
        {
            square = -1;
            country = string.Empty;
            foreach (var r in SquareAndCountry.Parse(str))
            {
                var i = (RealtyFromText)r;
                if (i.Square != -1)
                {
                    square = i.Square;
                }

                if (i.Country.Length != 0)
                {
                    country = i.Country;
                }
            }
        }

        public static decimal? ParseSquare(string strSquares)
        {
            ReadSquareAndCountry(strSquares, out var square, out var dummy);
            if (square != -1)
            {
                return square;
            }

            if (Regex.Match(strSquares, "[а-я]+", RegexOptions.IgnoreCase).Success)
            {
                return null;
            }

            var match = SquareRegexp.Match(strSquares);
            if (!match.Success)
            {
                return null;
            }

            square = decimal.Round(match.Value.ParseDecimalValue(), 2);
            return square == 0 ? null : (decimal?)square;
        }

        public static bool IsCountryStrict(string str) => CountryListParser.ParseToStringList(str).Count > 0;

        public static string ParseCountry(string str)
        {
            ReadSquareAndCountry(str, out var dummy, out var country);
            return country != string.Empty ? country : str;
        }

        public static bool ParseDocumentFileName(string filename, out int? documentfile_id, out string archive_file)
        {
            documentfile_id = null;
            archive_file = null;
            var filePath = Path.GetFullPath(filename);
            var dirName = new DirectoryInfo(Path.GetDirectoryName(filePath)).Name;
            var dirParseRes = int.TryParse(dirName, out var dirId);
            // dirty hack
            if (dirParseRes && (dirId > 2020 || dirId < 2000))
            {
                documentfile_id = int.Parse(dirName);
                archive_file = Path.GetFileName(filename);
                return true;
            }
            else
            {
                var res = int.TryParse(Path.GetFileNameWithoutExtension(filename), out var val);
                if (res)
                {
                    documentfile_id = val;
                }

                return res;
            }
        }
    }
}
