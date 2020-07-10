using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Text;
using TI.Declarator.ParserCommon;
using System.Linq;
using System.Text.RegularExpressions;
using System.Diagnostics;

namespace Smart.Parser.Lib
{
    public class RealtyParser : ParserBase
    {
        static readonly string OwnedString = "В собственности";
        static readonly string StateString = "В пользовании";
        public static void CheckProperty(RealEstateProperty prop)
        {
            if (prop == null)
            {
                return;
            }

        }

        string GetRealyTypeFromColumnTitle(DeclarationField fieldName)
        {
            if ((fieldName & DeclarationField.LandArea) > 0) { return "земельный участок"; }
            if ((fieldName & DeclarationField.LivingHouse) > 0) { return "земельный участок"; }
            if ((fieldName & DeclarationField.Appartment) > 0) { return "квартира"; }
            if ((fieldName & DeclarationField.SummerHouse) > 0) { return "дача"; }
            if ((fieldName & DeclarationField.Garage) > 0) { return "гараж"; }
            return null;
        }

        void AddRealEstateWithNaturalText(DataRow currRow, DeclarationField fieldName, string ownTypeByColumn, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(fieldName))
            {
                fieldName = fieldName | DeclarationField.MainDeclarant;
            }

            if (currRow.ColumnOrdering.ContainsField(fieldName))
            {
                string text = currRow.GetContents(fieldName).Trim().Replace("не имеет", "").Trim();
                if (!DataHelper.IsEmptyValue(text) && text != "0")
                {
                    foreach (var bulletText in FindBullets(text))
                    {
                        RealEstateProperty realEstateProperty = new RealEstateProperty();
                        realEstateProperty.Text = bulletText;
                        realEstateProperty.type_raw = GetRealyTypeFromColumnTitle(fieldName);
                        realEstateProperty.own_type_by_column = ownTypeByColumn;
                        var match = Regex.Match(bulletText, ".*\\s(\\d+[.,]\\d+)\\sкв.м", RegexOptions.IgnoreCase);
                        if (match.Success)
                        {
                            realEstateProperty.square = DataHelper.ConvertSquareFromString(match.Groups[1].ToString());
                        }

                        decimal? square = DataHelper.ParseSquare(bulletText);
                        if (square.HasValue)
                        {
                            realEstateProperty.square = square;
                        }

                        CheckProperty(realEstateProperty);
                        person.RealEstateProperties.Add(realEstateProperty);
                    }
                }
            }
        }

        public void ParseOwnedProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.OwnedRealEstateSquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.OwnedColumnWithNaturalText, OwnedString, person);
                return;
            }
            string estateTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateType).Replace("не имеет", "");
            string ownTypeStr = null;
            if (currRow.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                ownTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateOwnershipType).Replace("не имеет", "");
            }
            string squareStr = currRow.GetContents(DeclarationField.OwnedRealEstateSquare).Replace("не имеет", "");
            string countryStr = currRow.GetContents(DeclarationField.OwnedRealEstateCountry, false).Replace("не имеет", "");

            try
            {
                if (GetLinesStaringWithNumbers(squareStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, ownTypeStr, squareStr, countryStr, person, OwnedString);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, ownTypeStr, squareStr, countryStr, person, OwnedString);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }
        public void ParseRealtiesWithTypesInTitles(DataRow currRow, Person person)
        {

            if (currRow.ColumnOrdering.ContainsField(DeclarationField.MixedLandAreaSquare))
            {
                string squareStr = currRow.GetContents(DeclarationField.MixedLandAreaSquare);

            }

        }
        public void ParseMixedProperty(DataRow currRow, Person person)
        {
            DeclarationField[] fieldWithRealTypes = { DeclarationField.MixedLandAreaSquare,
                                                      DeclarationField.MixedLivingHouseSquare,
                                                      DeclarationField.MixedAppartmentSquare,
                                                      DeclarationField.MixedSummerHouseSquare,
                                                      DeclarationField.MixedGarageSquare };
            foreach (var f in fieldWithRealTypes)
            {
                if (!currRow.ColumnOrdering.ContainsField(DeclarationField.MixedRealEstateSquare))
                {
                    AddRealEstateWithNaturalText(currRow, f, null, person);
                }
            }

            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.MixedRealEstateSquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.MixedColumnWithNaturalText, null, person);
                return;
            }

            string estateTypeStr = currRow.GetContents(DeclarationField.MixedRealEstateType).Replace("не имеет", "");
            string squareStr = currRow.GetContents(DeclarationField.MixedRealEstateSquare).Replace("не имеет", "");
            string countryStr = currRow.GetContents(DeclarationField.MixedRealEstateCountry).Replace("не имеет", "");
            string owntypeStr = currRow.GetContents(DeclarationField.MixedRealEstateOwnershipType, false).Replace("не имеет", "");
            if (owntypeStr == "")
                owntypeStr = null;

            try
            {
                if (GetLinesStaringWithNumbers(squareStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, owntypeStr, squareStr, countryStr, person);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, owntypeStr, squareStr, countryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseStateProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.StatePropertySquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.StateColumnWithNaturalText, StateString, person);
                return;
            }
            string statePropTypeStr = currRow.GetContents(DeclarationField.StatePropertyType, false).Replace("не имеет", "");
            if (DataHelper.IsEmptyValue(statePropTypeStr))
            {
                return;
            }
            string statePropOwnershipTypeStr = currRow.GetContents(DeclarationField.StatePropertyOwnershipType, false).Replace("не имеет", "");
            string statePropSquareStr = currRow.GetContents(DeclarationField.StatePropertySquare).Replace("не имеет", "");
            string statePropCountryStr = currRow.GetContents(DeclarationField.StatePropertyCountry, false).Replace("не имеет", "");

            try
            {
                if (GetLinesStaringWithNumbers(statePropSquareStr).Count > 1)
                {
                    ParseStatePropertyManyValuesInOneCell(
                        statePropTypeStr,
                        statePropOwnershipTypeStr,
                        statePropSquareStr,
                        statePropCountryStr,
                        person);
                }
                else
                {
                    ParseStatePropertySingleRow(statePropTypeStr,
                        statePropOwnershipTypeStr,
                        statePropSquareStr,
                        statePropCountryStr,
                        person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        static public void ParseStatePropertySingleRow(string statePropTypeStr,
    string statePropOwnershipTypeStr,
    string statePropSquareStr,
    string statePropCountryStr,
    Person person)
        {
            statePropTypeStr = statePropTypeStr.Trim();
            if (DataHelper.IsEmptyValue(statePropTypeStr))
            {
                return;
            }
            RealEstateProperty stateProperty = new RealEstateProperty();


            stateProperty.Text = statePropTypeStr;
            stateProperty.type_raw = statePropTypeStr;
            stateProperty.square = DataHelper.ParseSquare(statePropSquareStr); ;
            stateProperty.square_raw = NormalizeRawDecimalForTest(statePropSquareStr);
            stateProperty.country_raw = DataHelper.ParseCountry(statePropCountryStr);
            if (statePropOwnershipTypeStr != "")
                stateProperty.own_type_raw = statePropOwnershipTypeStr;
            stateProperty.own_type_by_column = StateString;
            CheckProperty(stateProperty);
            person.RealEstateProperties.Add(stateProperty);
        }

        static public void ParseOwnedPropertySingleRow(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person, string ownTypeByColumn = null)
        {
            estateTypeStr = estateTypeStr.Trim();
            areaStr = areaStr.ReplaceEolnWithSpace();
            if (DataHelper.IsEmptyValue(estateTypeStr))
            {
                return;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.square = DataHelper.ParseSquare(areaStr);
            realEstateProperty.square_raw = NormalizeRawDecimalForTest(areaStr);
            realEstateProperty.country_raw = DataHelper.ParseCountry(countryStr);
            realEstateProperty.own_type_by_column = ownTypeByColumn;

            // колонка с типом недвижимости отдельно
            if (ownTypeStr != null)
            {
                realEstateProperty.type_raw = estateTypeStr;
                realEstateProperty.own_type_raw = ownTypeStr;
                realEstateProperty.Text = estateTypeStr;
            }
            else // колонка содержит тип недвижимости и тип собственности
            {
                realEstateProperty.Text = estateTypeStr;
            }

            realEstateProperty.Text = estateTypeStr;
            CheckProperty(realEstateProperty);
            person.RealEstateProperties.Add(realEstateProperty);
        }
        static List<int> GetLinesStaringWithNumbers(string areaStr)
        {
            List<int> linesWithNumbers = new List<int>();
            string[] lines = areaStr.Split('\n');
            for (int i = 0; i < lines.Count(); ++i)
            {
                if (Regex.Matches(lines[i], "^\\s*[1-9]").Count > 0) // not a zero in the begining
                {
                    linesWithNumbers.Add(i);
                }
            }
            return linesWithNumbers;

        }

        static string[] FindBullets(string text)
        {
            return Regex.Split(text, "\n\\s?[0-9][0-9]?[.)]");
        }

        static string SliceArrayAndTrim(string[] lines, int start, int end)
        {
            return String.Join("\n", lines.Skip(start).Take(end - start)).ReplaceEolnWithSpace();
        }

        static List<string> DivideByBordersOrEmptyLines(string value, List<int> linesWithNumbers)
        {
            var result = new List<string>();
            if (value == null)
            {
                return result;
            }
            var lines = SplitJoinedLinesByFuzzySeparator(value, linesWithNumbers);
            Debug.Assert(linesWithNumbers.Count > 1);
            int startLine = linesWithNumbers[0];
            int numberIndex = 1;
            string item;
            for (int i = startLine + 1; i < lines.Count(); ++i)
            {
                item = SliceArrayAndTrim(lines, startLine, i);
                if (item.Count() > 0) // not empty item
                {
                    if ((numberIndex < linesWithNumbers.Count && i == linesWithNumbers[numberIndex]) || lines[i].Trim().Count() == 0)
                    {
                        result.Add(item);
                        startLine = i;
                        numberIndex++;
                    }
                }
            }

            item = SliceArrayAndTrim(lines, startLine, lines.Count());
            if (item.Count() > 0) result.Add(item);

            if (result.Count < linesWithNumbers.Count)
            {
                var notEmptyLines = new List<string>();
                foreach (var l in lines)
                {
                    if (l.Trim(' ').Length > 0)
                    {
                        notEmptyLines.Add(l);
                    }
                }
                if (notEmptyLines.Count == linesWithNumbers.Count)
                {
                    return notEmptyLines;
                }
            }

            return result;
        }

        private static string[] SplitJoinedLinesByFuzzySeparator(string value, List<int> linesWithNumbers)
        {
            string[] lines;

            // Eg: "1. Квартира\n2. Квартира"
            if (Regex.Matches(value, @"^\d\.\s+.+\n\d\.\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"\d\.\s").Skip(1).ToArray();
                return lines;
            }

            // Eg: "- Квартира\n- Квартира"
            if (Regex.Matches(value, @"^\p{Pd}\s+.+\n\p{Pd}\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"\n\p{Pd}");
                return lines;
            }

            // Eg: "... собственность) - Жилой дом ..."
            if (Regex.Matches(value, @"^\p{Pd}.+\)[\s\n]+\p{Pd}\s", RegexOptions.Singleline).Count > 0)
            {
                lines = (string[])Regex.Split(value, @"[\s\n]\p{Pd}\s");
                return lines;
            }

            // Eg: "Квартира \n(долевая собственность \n\n0,3) \n \n \n \nКвартира \n(индивидуальная собственность) \n"
            var matches = Regex.Matches(value, @"[^\)]+\([^\)]+\)\;?", RegexOptions.Singleline);
            if (matches.Count == linesWithNumbers.Count)
            {
                lines = matches.Select(m => m.Value).ToArray();
                return lines;
            }

            lines = value.Trim(' ', ';').Split(';');
            if (lines.Length != linesWithNumbers.Count)
            {
                lines = value.Split('\n');
            }

            return lines;
        }

        static string GetListValueOrDefault(List<string> body, int index, string defaultValue)
        {
            if (index >= body.Count)
            {
                return defaultValue;
            }
            else
            {
                return body[index];
            }
        }

        static public void ParseOwnedPropertyManyValuesInOneCell(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person, string ownTypeByColumn = null)
        {
            List<int> linesWithNumbers = GetLinesStaringWithNumbers(areaStr);
            List<string> estateTypes = DivideByBordersOrEmptyLines(estateTypeStr, linesWithNumbers);
            List<string> areas = DivideByBordersOrEmptyLines(areaStr, linesWithNumbers);
            List<string> ownTypes = DivideByBordersOrEmptyLines(ownTypeStr, linesWithNumbers);
            List<string> countries = DivideByBordersOrEmptyLines(countryStr, linesWithNumbers);
            for (int i = 0; i < areas.Count; ++i)
            {
                ParseOwnedPropertySingleRow(
                    GetListValueOrDefault(estateTypes, i, ""),
                    GetListValueOrDefault(ownTypes, i, null),
                    GetListValueOrDefault(areas, i, ""),
                    GetListValueOrDefault(countries, i, ""),
                    person,
                    ownTypeByColumn
                );
            }
        }
        static public void ParseStatePropertyManyValuesInOneCell(string estateTypeStr,
            string ownTypeStr,
            string areaStr,
            string countryStr,
            Person person)
        {
            List<int> linesWithNumbers = GetLinesStaringWithNumbers(areaStr);
            List<string> estateTypes = DivideByBordersOrEmptyLines(estateTypeStr, linesWithNumbers);
            List<string> estateOwnTypes = DivideByBordersOrEmptyLines(ownTypeStr, linesWithNumbers);
            List<string> areas = DivideByBordersOrEmptyLines(areaStr, linesWithNumbers);
            List<string> countries = DivideByBordersOrEmptyLines(countryStr, linesWithNumbers);
            for (int i = 0; i < areas.Count; ++i)
            {
                ParseStatePropertySingleRow(
                    GetListValueOrDefault(estateTypes, i, ""),
                    GetListValueOrDefault(estateOwnTypes, i, ""),
                    GetListValueOrDefault(areas, i, ""),
                    GetListValueOrDefault(countries, i, ""),
                    person
                );
            }
        }


    }
}
