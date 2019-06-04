﻿using Parser.Lib;
using System;
using System.Collections.Generic;
using System.IO;
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
            // Исправляем инициал, слипшийся с фамилией БуровЮ.В.
            Regex regex = new Regex("([а-я])([А-Я]\\.)", RegexOptions.Compiled);

            nameOrRelativeType = regex.Replace(nameOrRelativeType, delegate(Match m) {
                return m.Groups[1].Value + " "+ m.Groups[2].Value;
            });

            // Исправляем слипшийся инициалы с фамилией Буров ЮВ
            Regex regex2 = new Regex("( [А-Я])([А-Я])$", RegexOptions.Compiled);

            nameOrRelativeType = regex2.Replace(nameOrRelativeType, delegate (Match m) {
                return m.Groups[1].Value + " " + m.Groups[2].Value;
            });

            // Ибрагимов С.-Э.С.-А.

            var parts = nameOrRelativeType.Split(new char[] { ' ', '.', ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Count() == 3 &&
                parts[0].Length > 1 &&
                parts[1].Length == 1 && 
                parts[2].Length == 1)
            {
                return true;
            };
            int parts_count = parts.Where(s => s.Length > 2 ).Count();
            bool threePart = parts_count == 3;
            if (threePart)
            {
                return true;
            }
            if (parts_count == 4)
            {
                return true;
            }
            if (parts_count == 2)
            {
                return true;
            }


            bool onlySecondName = (parts_count == 1) && (ParseRelationType(nameOrRelativeType, false) == RelationType.Error);
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
                case "племяница супруги": return RelationType.MaleSpouse;
                case "подопечный": return RelationType.MaleSpouse;
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

        public static decimal? ParseDeclaredIncome(string strIncome)
        {
            Decimal result;
            if (String.IsNullOrWhiteSpace(strIncome) || strIncome.Trim() == "-" || strIncome.Trim() == "–" ||
                strIncome.Trim() == "не имеет")
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

            return Decimal.Round(result, 2);

        }
        public static string ParseDataSources(string src)
        {
            if (src.Trim() == "-") return null;
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
/*
            if (PropertyDictionary.ParseParseRealEstateType(key, out type))
            {
                return type;
            }
            throw new UnknownRealEstateTypeException(key);
            */
        }

        public static OwnershipType TryParseOwnershipType(string strOwn, OwnershipType defaultType = OwnershipType.None)
        {
            string str = strOwn.ToLower().Trim();
            if (String.IsNullOrWhiteSpace(str) || str == "-")
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
            /*
            var parts2 = Regex.Split(str, "[ 0-9,\\(\\)]+");
            foreach (var s in parts2.Reverse())
            {
                OwnershipType res = DeclaratorApiPatterns.TryParseOwnershipType(s);
                if (res != OwnershipType.None)
                {
                    result = res;
                }
            }
            */

            //if (res == OwnershipType.None)
            //    throw new UnknownOwnershipTypeException(strOwn);


            return defaultType;
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
                "а/м"
            };
            vechicleString = vechicleString.Trim();
            var vehicleTypeRegex = new Regex("(" + string.Join("|", vehicleTypeDict) + ")", RegexOptions.IgnoreCase);
            string normalVehicleStr = vechicleString.ToLower().Trim();
            if (String.IsNullOrEmpty(normalVehicleStr) || 
                normalVehicleStr == "не имеет" ||
                normalVehicleStr == "-" ||
                normalVehicleStr == "_")
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

        static public bool ParseDocumentFileName(string filename, out int? id, out string archive_file)
        {
            id = null;
            archive_file = null;

            char[] separators = new char[] {
                Path.DirectorySeparatorChar,
                Path.AltDirectorySeparatorChar
            };

            string[] folders = filename.Split(separators, StringSplitOptions.RemoveEmptyEntries);

            List<string> rest = new List<string>();
            bool procRest = false;
            foreach (var f in folders)
            {
                if (procRest)
                {
                    rest.Add(f);
                }
                var match = Regex.Match(f, @"(^\d+)(\.|$)");
                if (match.Success)
                {
                    rest.Clear();
                    string number = match.Groups[1].Value;
                    id = int.Parse(number);
                    procRest = true;
                }
            }
            if (!procRest)
            {
                return false;
            }

            if (rest.Count > 0)
            {
                archive_file = string.Join(Path.DirectorySeparatorChar.ToString(), rest);
            }

            return true;
        }
    }
}
