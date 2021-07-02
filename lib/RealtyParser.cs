using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using TI.Declarator.ParserCommon;
using SmartAntlr;

namespace Smart.Parser.Lib
{
    public class TRealtyCell
    {
        public Cell DataCell = null;
        public List<string> ParsedItems;
        public string DefaultValue;

        public TRealtyCell(Cell cell)
        {
            DataCell = cell;
            ParsedItems = new List<string>();
            DefaultValue = "";
        }

        public string GetDataCellText()
        {
            if (DataCell != null)
            {
                return DataCell.GetText(true);
            }
            else
            {
                return "";
            }
        }
        public string GetParsedItem(int index)
        {
            if (index >= ParsedItems.Count)
            {
                return DefaultValue;
            }
            else
            {
                return ParsedItems[index];
            }
        }
        public void SetDefaultValueIfUnique()
        {
            var uniqValues = new HashSet<string>(ParsedItems);
            if (uniqValues.Count == 1)
            {
                DefaultValue = uniqValues.First<string>();
            }

        }

        public void ParseByEmptyLines(List<int> linesWithNumbers)
        {
            if (DataCell == null)
            {
                for (int i=0; i < linesWithNumbers.Count; ++i)
                {
                    ParsedItems.Add(null);
                }
                return;
            }
            ParsedItems = DataCell.SplitJoinedLinesByFuzzySeparator(linesWithNumbers).ToList<string>();
        }
        public void ParseByAntlr(GeneralAntlrParserWrapper parser)
        {
            if (DataCell != null)
            {
                ParsedItems = parser.ParseToStringList(GetDataCellText());
            }
        }
        public void CopyUnparsedValue()
        {
            if (DataCell != null)
            {
                ParsedItems.Add(DataCell.GetText(true));
            }
        }
    }
    
    public class TRealtyCellSpan
    {
        public static readonly string OwnedString = "В собственности";
        public static readonly string StateString = "В пользовании";

        public ParserBase Parent;
        public TRealtyCell EstateTypeCell = null;
        public TRealtyCell OwnTypeCell = null;
        public TRealtyCell SquareCell = null;
        public TRealtyCell CountryCell = null;
        public TRealtyCellSpan( Cell estateTypeCell, Cell ownTypeCell, Cell squareCell, Cell countryCell)
        {
            if (squareCell != null && countryCell != null)
            {
                if (CountryAndSquareAreSwapped(squareCell.GetText(true), countryCell.GetText(true)))
                {
                    (squareCell, countryCell) = (countryCell, squareCell);
                }
            }

            EstateTypeCell = new TRealtyCell(estateTypeCell);
            OwnTypeCell = new TRealtyCell(ownTypeCell);
            SquareCell = new TRealtyCell(squareCell);
            CountryCell = new TRealtyCell(countryCell);
            if (!ShouldStartParsing())
            {
                EstateTypeCell.CopyUnparsedValue();
                OwnTypeCell.CopyUnparsedValue();
                SquareCell.CopyUnparsedValue();
                CountryCell.CopyUnparsedValue();
            }
            else
            {
                ParseCellTexts();
            }
            CountryCell.SetDefaultValueIfUnique();

        }
        void ParseCellTexts()
        {
            List<int> linesWithNumbers = GetLinesStaringWithNumbers(SquareCell.DataCell.GetText(true));
            if (linesWithNumbers.Count > 1)
            {
                EstateTypeCell.ParseByEmptyLines(linesWithNumbers);
                OwnTypeCell.ParseByEmptyLines(linesWithNumbers);
                SquareCell.ParseByEmptyLines(linesWithNumbers);
                CountryCell.ParseByEmptyLines(linesWithNumbers);
            }
            else
            {
                SquareCell.ParseByAntlr(new AntlrSquareParser());
                if (OwnTypeCell.DataCell != null)
                {
                    EstateTypeCell.ParseByAntlr(new AntlrRealtyTypeParser());
                    OwnTypeCell.ParseByAntlr(new AntlrOwnTypeParser());
                }
                else
                {
                    foreach (var r in new AntlrRealtyTypeAndOwnTypeParser().Parse(EstateTypeCell.DataCell.GetText(true)))
                    {
                        var i = (RealtyTypeAndOwnTypeFromText)r;
                        EstateTypeCell.ParsedItems.Add(i.RealtyType);
                        OwnTypeCell.ParsedItems.Add(i.OwnType);
                    }

                }
                CountryCell.ParseByAntlr(new AntlrCountryListParser());
            }
        }

        static public bool CountryAndSquareAreSwapped(string squareStr, string countryStr)
        {
            return ((squareStr.ToLower().Trim() == "россия" ||
                 squareStr.ToLower().Trim() == "рф") &&
                Regex.Match(countryStr.Trim(), @"[0-9,.]").Success);
        }

        public static List<int> GetLinesStaringWithNumbers(string areaStr)
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
        public bool ShouldStartParsing()
        {
            if (CountryCell.GetDataCellText().Length > 0)
            {
                if (new AntlrCountryListParser().ParseToStringList(CountryCell.GetDataCellText()).Count > 1)
                {
                    // может быть одна страна на все объекты недвижимости
                    return true;
                }
            }
            return GetLinesStaringWithNumbers(SquareCell.GetDataCellText()).Count > 1;
        }
        public void ParseOwnedPropertySingleRow(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person, string ownTypeByColumn = null)
        {
            estateTypeStr = estateTypeStr.Trim().Trim('-', ' ');
            areaStr = areaStr.ReplaceEolnWithSpace();
            if (DataHelper.IsEmptyValue(estateTypeStr))
            {
                return;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.square = DataHelper.ParseSquare(areaStr);
            realEstateProperty.square_raw = ParserBase.NormalizeRawDecimalForTest(areaStr);
            realEstateProperty.country_raw = DataHelper.ParseCountry(countryStr).NormSpaces();
            realEstateProperty.own_type_by_column = ownTypeByColumn;

            // колонка с типом недвижимости отдельно
            if (ownTypeStr != null)
            {
                realEstateProperty.type_raw = estateTypeStr.NormSpaces();
                realEstateProperty.own_type_raw = ownTypeStr.NormSpaces(); 
                realEstateProperty.Text = estateTypeStr.NormSpaces();
            }
            else // колонка содержит тип недвижимости и тип собственности
            {
                realEstateProperty.Text = estateTypeStr.NormSpaces();
                if (realEstateProperty.Text.ToLower().Contains("пользовани")) {
                    realEstateProperty.own_type_raw = TRealtyCellSpan.StateString;
                }
            }

            realEstateProperty.Text = estateTypeStr.NormSpaces();
            person.RealEstateProperties.Add(realEstateProperty);
        }
        public void ParseStatePropertySingleRow(string statePropTypeStr,string statePropOwnershipTypeStr,
                    string statePropSquareStr, string statePropCountryStr,Person person)
        {

            statePropTypeStr = statePropTypeStr.Trim();
            if (DataHelper.IsEmptyValue(statePropTypeStr))
            {
                return;
            }
            RealEstateProperty stateProperty = new RealEstateProperty();

            statePropTypeStr = statePropTypeStr.Trim(' ', '-');
            stateProperty.Text = statePropTypeStr.NormSpaces();
            stateProperty.type_raw = statePropTypeStr.NormSpaces();
            stateProperty.square = DataHelper.ParseSquare(statePropSquareStr); ;
            stateProperty.square_raw = ParserBase.NormalizeRawDecimalForTest(statePropSquareStr);
            stateProperty.country_raw = DataHelper.ParseCountry(statePropCountryStr).NormSpaces();
            if (statePropOwnershipTypeStr != "" && statePropOwnershipTypeStr != null)
                stateProperty.own_type_raw = statePropOwnershipTypeStr.NormSpaces();
            stateProperty.own_type_by_column = StateString;
            person.RealEstateProperties.Add(stateProperty);
        }

        int GetMaxDataItemsCount()
        {
            return Math.Max(SquareCell.ParsedItems.Count, EstateTypeCell.ParsedItems.Count);
        }

        public void ParseOwnedPropertyManyValuesInOneCell(Person person, string ownTypeByColumn = null)
        {
            for (int i = 0; i < GetMaxDataItemsCount(); ++i)
            {
                ParseOwnedPropertySingleRow(
                    EstateTypeCell.GetParsedItem(i),
                    OwnTypeCell.GetParsedItem(i),
                    SquareCell.GetParsedItem(i),
                    CountryCell.GetParsedItem(i),
                    person,
                    ownTypeByColumn
                );
            }
        }

        public void ParseStatePropertyManyValuesInOneCell(Person person)
        {
            for (int i = 0; i < GetMaxDataItemsCount(); ++i)
            {
                ParseStatePropertySingleRow(
                    EstateTypeCell.GetParsedItem(i),
                    OwnTypeCell.GetParsedItem(i),
                    SquareCell.GetParsedItem(i),
                    CountryCell.GetParsedItem(i),
                    person
                );
            }
        }

    }

    public class RealtyParser : ParserBase
    {

        string GetRealtyTypeFromColumnTitle(DeclarationField fieldName)
        {
            if ((fieldName & DeclarationField.LandArea) > 0) { return "земельный участок"; }
            if ((fieldName & DeclarationField.LivingHouse) > 0) { return "земельный участок"; }
            if ((fieldName & DeclarationField.Appartment) > 0) { return "квартира"; }
            if ((fieldName & DeclarationField.SummerHouse) > 0) { return "дача"; }
            if ((fieldName & DeclarationField.Garage) > 0) { return "гараж"; }
            return null;
        }

        void ParseRealtiesDistributedByColumns(string ownTypeByColumn, string realtyTypeFromColumnTitle, string cellText, Person person)
        {
            foreach (var bulletText in FindBullets(cellText))
            {
                RealEstateProperty realEstateProperty = new RealEstateProperty();
                realEstateProperty.Text = bulletText;
                realEstateProperty.type_raw = realtyTypeFromColumnTitle;
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

                person.RealEstateProperties.Add(realEstateProperty);
            }
        }
        void ParseRealtiesByAntlr(string ownTypeByColumn, string cellText, Person person)
        {
            var parser = new AntlrStrictParser();
            foreach (var item in parser.Parse(cellText))
            {
                RealtyFromText realty = (RealtyFromText)item;
                if (realty.RealtyType != null && realty.RealtyType.Length > 0)
                {
                    RealEstateProperty realEstateProperty = new RealEstateProperty();
                    realEstateProperty.Text = realty.GetSourceText();
                    realEstateProperty.type_raw = realty.RealtyType;
                    realEstateProperty.square = realty.Square;
                    realEstateProperty.country_raw = realty.Country;
                    realEstateProperty.own_type_raw = realty.OwnType;
                    //???  = realty.RealtyShare; // nowhere to write to
                    realEstateProperty.own_type_by_column = ownTypeByColumn;
                    person.RealEstateProperties.Add(realEstateProperty);
                }
            }
        }

        void AddRealEstateWithNaturalText(DataRow currRow, DeclarationField fieldName, string ownTypeByColumn, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(fieldName))
            {
                fieldName = fieldName | DeclarationField.MainDeclarant;
            }

            if (!currRow.ColumnOrdering.ContainsField(fieldName)) {
                return;
            }
            string text = currRow.GetContents(fieldName).Trim().Replace("не имеет", "").Trim();
            if (DataHelper.IsEmptyValue(text) || text == "0") {
                return;
            }
            var realtyType = GetRealtyTypeFromColumnTitle(fieldName);
            if (realtyType != null) {
                ParseRealtiesDistributedByColumns(ownTypeByColumn, realtyType, text, person);
            }
            else
            {
                ParseRealtiesByAntlr(ownTypeByColumn, text, person);

            }
        }

        public void ParseOwnedOrMixedProperty(Cell estateTypeCell, Cell ownTypeCell, Cell squareCell, Cell countryCell, 
            DataRow currRow, Person person, string ownTypeByColumn = null)
        {
            try
            {
                var cellSpan = new TRealtyCellSpan(estateTypeCell, ownTypeCell, squareCell, countryCell);
                cellSpan.ParseOwnedPropertyManyValuesInOneCell(person, ownTypeByColumn);
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseOwnedProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.OwnedRealEstateSquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.OwnedColumnWithNaturalText, TRealtyCellSpan.OwnedString, person);
                return;
            }
            var estateTypeCell = currRow.GetDeclarationField(DeclarationField.OwnedRealEstateType);
            Cell ownTypeCell = null;
            if (currRow.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                ownTypeCell = currRow.GetDeclarationField(DeclarationField.OwnedRealEstateOwnershipType);
            }
            var squareCell = currRow.GetDeclarationField(DeclarationField.OwnedRealEstateSquare);
            var countryCell = currRow.GetDeclarationField(DeclarationField.OwnedRealEstateCountry, false);
            ParseOwnedOrMixedProperty(estateTypeCell, ownTypeCell, squareCell, countryCell, currRow, person, TRealtyCellSpan.OwnedString);
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

            Cell estateTypeCell = currRow.GetDeclarationField(DeclarationField.MixedRealEstateType);
            Cell squareCell = currRow.GetDeclarationField(DeclarationField.MixedRealEstateSquare);
            Cell countryCell = currRow.GetDeclarationField(DeclarationField.MixedRealEstateCountry);
            Cell owntypeCell = currRow.GetDeclarationField(DeclarationField.MixedRealEstateOwnershipType, false);
            ParseOwnedOrMixedProperty(estateTypeCell, owntypeCell, squareCell, countryCell, currRow, person);
        }


        public void ParseStateProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.StatePropertySquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.StateColumnWithNaturalText, TRealtyCellSpan.StateString, person);
                return;
            }
            Cell statePropTypeCell = currRow.GetDeclarationField(DeclarationField.StatePropertyType, false);
            if (statePropTypeCell == null || DataHelper.IsEmptyValue(statePropTypeCell.GetText(true)))
            {
                return;
            }
            Cell ownershipTypeCell = currRow.GetDeclarationField(DeclarationField.StatePropertyOwnershipType, false);
            Cell squareCell = currRow.GetDeclarationField(DeclarationField.StatePropertySquare);
            Cell countryCell = currRow.GetDeclarationField(DeclarationField.StatePropertyCountry, false);

           
            try
            {
                var cellSpan = new TRealtyCellSpan(statePropTypeCell, ownershipTypeCell, squareCell, countryCell);
                cellSpan.ParseStatePropertyManyValuesInOneCell(person);
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        static string[] FindBullets(string text)
        {
            return Regex.Split(text, "\n\\s?[0-9][0-9]?[.)]");
        }
    }
}
