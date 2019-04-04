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
            // Исправляем инициал, слипшийся с фамилией БуровЮ.В.
            Regex regex = new Regex("([а-я])([А-Я]\\.)", RegexOptions.Compiled);

            nameOrRelativeType = regex.Replace(nameOrRelativeType, delegate(Match m) {
                return m.Groups[1].Value + " "+ m.Groups[2].Value;
            });

            // Исправляем слипшийся инициалы с фамилией Буров ЮВ
            Regex regex2 = new Regex("( [А-Я])([А-Я])", RegexOptions.Compiled);

            nameOrRelativeType = regex2.Replace(nameOrRelativeType, delegate (Match m) {
                return m.Groups[1].Value + " " + m.Groups[2].Value;
            });


            int parts = nameOrRelativeType.Split(new char[] { ' ', '.', ',' }, StringSplitOptions.RemoveEmptyEntries).Count();
            bool threePart = parts == 3;
            if (threePart)
            {
                return true;
            }
            if (parts == 4)
            {
                return true;
            }
            if (parts == 2)
            {
                return true;
            }


            bool onlySecondName = (parts == 1) && (ParseRelationType(nameOrRelativeType, false) == RelationType.Error);
            if (onlySecondName)
            {
                return true;
            }

            return false;
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
            switch (strRel.ToLower().Replace("  ", " ").Trim().RemoveStupidTranslit())
            {
                case "супруг": return RelationType.MaleSpouse;
                case "суруга": return RelationType.FemaleSpouse;
                case "супруга": return RelationType.FemaleSpouse;
                case "несовершен-нолетняя дочь": return RelationType.Child;
                case "несовершенно-летняя дочь": return RelationType.Child;
                case "несовершеннолет-няя дочь": return RelationType.Child;
                case "несовершеннолетняя дочь": return RelationType.Child;
                case "несовершенно-летний сын": return RelationType.Child;
                case "несовершеннолет-ний сын": return RelationType.Child;
                case "несовершеннолетний сын": return RelationType.Child;
                case "несовершеннолетний ребенок": return RelationType.Child;
                case "несовершенолетний ребенок": return RelationType.Child;
                case "дочь": return RelationType.Child;
                case "дочь супроги": return RelationType.Child;
                case "дочь супруги": return RelationType.Child;
                case "сын супруги": return RelationType.Child;
                case "сын": return RelationType.Child;
                case "падчерица": return RelationType.Child;
                case "сын жены": return RelationType.Child;
                case "дочь жены": return RelationType.Child;
                case "несовершеннолетний ребёнок": return RelationType.Child;
                default:
                    if (throwException)
                    {
                        throw new ArgumentOutOfRangeException(strRel, $"Неизвестный тип родственника: {strRel}");
                    }
                    return RelationType.Error;
            }
        }

        public static decimal? ParseDeclaredIncome(string strIncome)
        {
            Decimal result;
            if (String.IsNullOrWhiteSpace(strIncome) || strIncome.Trim() == "-" || strIncome.Trim() == "–")
                return null;
            else
            {
                try
                {
                    int leftParenPos = strIncome.IndexOf("(");
                    if (leftParenPos == -1)
                    {
                        result = strIncome.ParseDecimalValue();
                    }
                    else
                    {
                        result = strIncome.Substring(0, leftParenPos).ParseDecimalValue();
                    }
                }
                catch (Exception)
                {
                    return null; 
                }

            }

            result = 1;
            return Decimal.Round(result, 2);

        }
        public static string ParseDataSources(string src)
        {
            if (src.Trim() == "-") return null;
            else return src;
        }


        public static IEnumerable<RealEstateType> ParseRealEstateTypes(string strTypes)
        {
            return new List<RealEstateType>() { DeclaratorApiPatterns.ParseRealEstateType(strTypes) };
        }

        public static RealEstateType ParseRealEstateType(string strType)
        {
            RealEstateType type = TryParseRealEstateType(strType);

            if (type == RealEstateType.None)
            {
                throw new UnknownRealEstateTypeException(strType);
            }
            return type;
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
/*
            if (PropertyDictionary.ParseParseRealEstateType(key, out type))
            {
                return type;
            }
            throw new UnknownRealEstateTypeException(key);
            */
        }

        public static IEnumerable<OwnershipType> ParseOwnershipTypes(string strOwn)
        {
            return new List<OwnershipType>() { ParseOwnershipType(strOwn) };
        }


        public static OwnershipType ParseOwnershipTypeAndShare(string strOwn, out string share)
        {
            var parts = Regex.Split(strOwn, "[ ,]+");
            OwnershipType res = DeclaratorApiPatterns.ParseOwnershipType(parts[0]);
            if (parts.Length > 1)
                share = parts[1];
            else
                share = "";

            return res;
        }
        public static OwnershipType ParseOwnershipType(string strOwn)
        {
            OwnershipType ownershipType = TryParseOwnershipType(strOwn);
            if (ownershipType == OwnershipType.None)
                throw new UnknownOwnershipTypeException(strOwn);
            return ownershipType;
        }

        public static OwnershipType TryParseOwnershipType(string strOwn)
        {
            string str = strOwn.ToLower().Trim();
            if (String.IsNullOrWhiteSpace(str) || str == "-")
                return OwnershipType.InUse;

            //var parts = Regex.Split(str, "[ ,]+");
            var parts = Regex.Split(str, "[0-9,\\(\\)]+");

            OwnershipType result = OwnershipType.None;
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
            var parts2 = Regex.Split(str, "[ 0-9,\\(\\)]+");
            foreach (var s in parts2)
            {
                OwnershipType res = DeclaratorApiPatterns.TryParseOwnershipType(s);
                if (res != OwnershipType.None)
                {
                    result = res;
                }
            }

            //if (res == OwnershipType.None)
            //    throw new UnknownOwnershipTypeException(strOwn);


            return result;
            /*

            if (PropertyDictionary.ParseParseRealEstateType(key, out type))
            {
                return type;
            }

            if (str.Contains("индивид")) res = OwnershipType.Individual;
            else if (str.Contains("собственность")) res = OwnershipType.Individual;
            else if (str.Contains("общая совместная")) res = OwnershipType.Coop;
            else if (str.Contains("совместная")) res = OwnershipType.Coop;

            else if (str.Contains("делевая")) res = OwnershipType.Shared;
            else if (str.Contains("долевая")) res = OwnershipType.Shared;
            else if (str.Contains("долеявая")) res = OwnershipType.Shared;
            else if (str.Contains("общая долевая")) res = OwnershipType.Shared;
            else if (str.Contains("общая, долевая")) res = OwnershipType.Shared;
            else if (str.Contains("общедолевая")) res = OwnershipType.Shared;

            else if (str.Contains("общая")) res = OwnershipType.Coop;

            else if (String.IsNullOrWhiteSpace(str) || str == "-") res = OwnershipType.NotAnOwner;
            else throw new ArgumentOutOfRangeException("strOwn", $"Неизвестный тип собственности: {strOwn}");

            return res;
            */
        }
        /*
        static public Tuple<RealEstateType, OwnershipType, string> ParsePropertyAndOwnershipType(string strPropInfo)
        {
            int leftParenPos = strPropInfo.IndexOf('(');
            string strPropType = strPropInfo.Substring(0, leftParenPos > 0 ? leftParenPos : strPropInfo.Length).Trim();
            RealEstateType realEstateType = ParseRealEstateType(strPropType);
            OwnershipType ownershipType = OwnershipType.Individual;
            string share = "1";

            int rightParenPos = -1;
            if (leftParenPos != -1)
            {
                rightParenPos = strPropInfo.IndexOf(')', leftParenPos);
                if (rightParenPos == -1)
                {
                    throw new Exception($"Expected closing parenthesis after left parenthesis was encountered at pos#{leftParenPos} in string {strPropInfo}");
                }

                string strOwnType = strPropInfo.Substring(leftParenPos + 1, rightParenPos - leftParenPos - 1);
                if (ContainsOwnershipType(strOwnType))
                {
                    ownershipType = ParseOwnershipType(strOwnType);
                    share = ParseOwnershipShare(strOwnType, ownershipType);

                }
            }

            return Tuple.Create(realEstateType, ownershipType, share);
        }

        */

        /*
         *  "квартира           (безвозмездное, бессрочное пользование)"
         *  
         *  "Квартира долевая , 2/3"
         *  
            квартира
            (совместная)  
         */
        static public Tuple<RealEstateType, OwnershipType, string> ParseCombinedRealEstateColumn(string strPropInfo)
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
                ownershipType = OwnershipType.Ownership;
            }
            return Tuple.Create(realEstateType, ownershipType, share);
        }

        static public List<Tuple<RealEstateType, OwnershipType, string>> ParsePropertyAndOwnershipTypes(string strPropInfo)
        {
            var res = new List<Tuple<RealEstateType, OwnershipType, string>>();


            int startingPos = 0;
            int rightParenPos = -1;
            int leftParenPos = strPropInfo.IndexOf('(', startingPos);
            bool containOwnershipType = ContainsOwnershipType(strPropInfo);


            if (leftParenPos < 0 && !containOwnershipType)
            {
                RealEstateType realEstateType = ParseRealEstateType(strPropInfo);
                OwnershipType ownershipType = OwnershipType.Individual;
                string share = "1";
                res.Add(Tuple.Create(realEstateType, ownershipType, share));

                return res;
            }
            //if (strPropInfo.Contains(","))
            //{
            //    string[] values = strPropInfo.Split(',');
            //    RealEstateType realEstateType = ParseRealEstateType(values[0]);
            //    OwnershipType ownershipType = ParseOwnershipType(strPropInfo);
            //    string share = ParseOwnershipShare(values[1], ownershipType);
            //    res.Add(Tuple.Create(realEstateType, ownershipType, share));
            //}

            while (leftParenPos != -1)
            {
                rightParenPos = strPropInfo.IndexOf(')', leftParenPos);
                if (rightParenPos == -1)
                {
                    throw new Exception($"Expected closing parenthesis after left parenthesis was encountered at pos#{leftParenPos} in string {strPropInfo}");
                }

                string strOwnType = strPropInfo.Substring(leftParenPos + 1, rightParenPos - leftParenPos - 1);
                string strPropType = strPropInfo.Substring(startingPos, leftParenPos - startingPos).Trim();

                //if (ContainsOwnershipType(strOwnType))
                {
                    RealEstateType realEstateType = ParseRealEstateType(strPropType);
                    OwnershipType ownershipType = ParseOwnershipType(strOwnType);
                    string share = ParseOwnershipShare(strOwnType, ownershipType);
                    res.Add(Tuple.Create(realEstateType, ownershipType, share));

                    startingPos = rightParenPos + 1;
                }

                leftParenPos = strPropInfo.IndexOf('(', rightParenPos + 1);
            }

            if (res.Count() == 0)
            {
                throw new Exception("func ParsePropertyAndOwnershipTypes: cannot parse " + strPropInfo);
            }

            return res;
        }

        static public IEnumerable<RealEstateType> ParseStatePropertyTypesWithUsageInfo(string strPropInfo)
        {
            var res = new List<RealEstateType>();

            int startingPos = 0;
            int rightParenPos = -1;
            int leftParenPos = strPropInfo.IndexOf('(', startingPos);
            while (leftParenPos != -1)
            {
                rightParenPos = strPropInfo.IndexOf(')', leftParenPos);
                if (rightParenPos == -1)
                {
                    throw new Exception($"Expected closing parenthesis after left parenthesis was encountered at pos#{leftParenPos} in string {strPropInfo}");
                }

                string strOwnType = strPropInfo.Substring(leftParenPos + 1, rightParenPos - leftParenPos - 1);
                if (ContainsOwnershipType(strOwnType))
                {
                    string strPropType = strPropInfo.Substring(startingPos, leftParenPos - startingPos);
                    RealEstateType realEstateType = ParseRealEstateType(strPropType);
                    res.Add(realEstateType);

                    startingPos = rightParenPos + 1;
                }

                leftParenPos = strPropInfo.IndexOf('(', rightParenPos + 1);
            }
            if (res.Count() == 0)
            {
                throw new Exception("Cannot parse string " + strPropInfo);
            }

            return res;
        }

        private static bool ContainsOwnershipType(string str)
        {
            string strProc = str.Trim().ToLower();
            return (str.Contains("индивид") || str.Contains("долевая") || str.Contains("общая"));
        }

        public static IEnumerable<string> ParseOwnershipShares(string strOwn, IEnumerable<OwnershipType> ownTypes)
        {
            var res = new List<string>();
            foreach (var ownType in ownTypes)
            {
                // FIXME на самом деле тут ещё нужно строковый параметр на отдельные подстроки разбивать
                res.Add(ParseOwnershipShare(strOwn, ownType));
            }

            return res;
        }

        public static string ParseOwnershipShare(string strOwn, OwnershipType ownType)
        {
            string res = strOwn;
            //if (ownType == OwnershipType.Shared)
            {
                /*
                String[] strToRemove = new String[] { "Общедолевая", "Общая долевая", "Общая, долевая", "Делевая", "Долевая", "Долеявая",
                                                      "Общая, долевая", "Доля", "Доли", "Долей", "Размер", " ", "(", ")" };
                foreach (string str in strToRemove)
                {
                    res = res.Replace(str, "");
                    res = res.Replace(str.ToLower(), "");
                }

                res = res.Trim(',');
                */
                var parts = Regex.Split(strOwn.ToLower().Trim(), "[ ,]+");
                //if (parts.Length > 1)
                //    return parts[1];

                var match = Regex.Match(strOwn, "\\d+/?\\d+");
                if (match.Success)
                {
                    return match.Value;
                }

                return "";
            }
            return "";
        }

        private static readonly string[] AreaSeparators = new string[] { "\n", " " };

        public static decimal? ParseArea(string strAreas)
        {
            if (Regex.Match(strAreas, "[а-я]+", RegexOptions.IgnoreCase).Success)
                return null;

            decimal? area = null;
            var match = Regex.Match(strAreas, "\\d+[,.]?(\\d+)?");
            if (match.Success)
            {

                Decimal d = match.Value.ParseDecimalValue();
                area = Decimal.Round(d, 2);
            }
            return area;
        }
        

        public static List<decimal?> ParseAreas(string strAreas)
        {
            var res = new List<decimal?>();
            foreach (var str in strAreas.Split(AreaSeparators, StringSplitOptions.RemoveEmptyEntries))
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
                else if (String.IsNullOrWhiteSpace(str) || str == "-")
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

        /*
        public static IEnumerable<Country> ParseCountries(string strCountries)
        {
            var res = new List<Country>();
            var parts = strCountries.Split(CountrySeparators, StringSplitOptions.RemoveEmptyEntries);

            foreach (var part in parts)
            {
                res.Add(ParseCountry(part));
            }

            return res;
        }
        public static Country ParseCountry(string strCountry)
        {
            Country country = TryParseCountry(strCountry);
            if (country == Country.Error)
            {
                throw new SmartParserException("Wrong country name: " + strCountry);
            }

            return country;
        }
        */
        public static Country TryParseCountry(string strCountry)
        {
            if (strCountry.Trim() == "" || strCountry.Trim() == "-")
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

    }
}
