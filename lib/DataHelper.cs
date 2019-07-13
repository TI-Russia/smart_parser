using Parser.Lib;
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
        static public bool IsPublicServantInfo(string nameOrRelativeType)
        {
            if (IsEmptyValue(nameOrRelativeType)) return false;

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
                case "супруг(а)": return RelationType.Spouse;
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
            if (Regex.Match(s, @"^[\s--]+$").Success)
            {
                return true;
            }
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
                var match = Regex.Match(str, "(\\d+)/(\\d+)");
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


        static public bool ParseDocumentFileName(string filename, out int? id, out string archive_file)
        {
            id = null;
            archive_file = null;
            string filePath = Path.GetFullPath(filename);
            string dirName = new DirectoryInfo(Path.GetDirectoryName(filePath)).Name;
            int dirId;
            bool dirParseRes = Int32.TryParse(dirName, out dirId);
            // dirty hack
            if (dirParseRes && (dirId > 2020 || dirId < 2000))
            {
                id = Int32.Parse(dirName);
                archive_file = Path.GetFileName(filename);
                return true;
            }
            else
            {
                int val;
                bool res = Int32.TryParse(Path.GetFileNameWithoutExtension(filename), out val);
                if (res) { id = val; }
                return res;
            }
        }
    }
}
