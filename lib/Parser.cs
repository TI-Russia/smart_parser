using CsvHelper;
using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.IO;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{

    public class Organization
    {

        public Organization(string name, string folder, int person_first, int person_last, bool topLevel)
        {
            this.name = name;
            this.folder = folder;
            this.person_first = person_first;
            this.person_last = person_last;
            this.topLevel = topLevel;
        }

        public string name;
        public string folder;
        public int person_first = -1;
        public int person_last = -1;
        public bool topLevel = false;
    };



    public class Parser
    {
        DateTime FirstPassStartTime;
        DateTime SecondPassStartTime;

        public int NameOrRelativeTypeColumn { set; get; } = 1;

        public Parser(IAdapter adapter)
        {
            Adapter = adapter;
        }

        public void DumpColumn(int column)
        {
            int personsTableEnd = Adapter.GetRowsCount() - 1;
            //StreamWriter standardOutput = new StreamWriter(Console.OpenStandardOutput());
            for (int i = 0; i <= personsTableEnd; i++)
            {
                //qDebug() << "person discovery - processing: " << cellAddress;
                Cell currentCell = Adapter.GetCell(i, NameOrRelativeTypeColumn);

                Console.WriteLine(JsonWriter.SerializeCell(currentCell));
            }
        }

        public void ExportCSV(string csvFile)
        {
            int rowCount = Adapter.GetRowsCount();
            int colCount = Adapter.GetColsCount();

            var stream = new FileStream(csvFile, FileMode.Create);
            var writer = new StreamWriter(stream) { AutoFlush = true };

            var csv = new CsvWriter(writer);

            for (int r = 0; r < rowCount; r++)
            {
                for (int c = 0; c < colCount; c++)
                {
                    string value = Adapter.GetCell(r, c).Text;
                    csv.WriteField(value);
                }
                csv.NextRecord();
            }
            csv.Flush();
        }
        public void SetMaxColumnsCountByHeader(int headerRowCount)
        {
            int maxfound = 0;
            for (int row = 0; row < headerRowCount; ++row)
            {
                for (int col = 0; col < 256; ++col)
                {
                    var c = Adapter.GetCell(row, col);
                    if (c == null)
                    {
                        break;
                    }
                    if (c.GetText() != "")
                    {
                        maxfound = Math.Max(col, maxfound);
                    }
                }
            }
            Adapter.MaxNotEmptyColumnsFoundInHeader = maxfound;
            Logger.Debug($"Set MaxNotEmptyColumnsFoundInHeader to {maxfound}");
        }



        public Declaration Parse()
        {
            FirstPassStartTime = DateTime.Now;
            DeclarationProperties properties = new DeclarationProperties()
            {
                Title = Adapter.ColumnOrdering.Title,
                MinistryName = Adapter.ColumnOrdering.MinistryName,
                Year = Adapter.ColumnOrdering.Year,
                SheetName = Adapter.GetWorksheetName()
            };
            if (properties.Year == null)
            {
                var incomeHeader = Adapter.Rows[0].GetContents(DeclarationField.DeclaredYearlyIncome);
                string dummy = "";
                int? year = null;
                ColumnDetector.GetValuesFromTitle(incomeHeader, ref dummy, ref year, ref dummy);
                properties.Year = year;
            }

            Declaration declaration = new Declaration()
            {
                Properties = properties
            };
            totalIncome = 0;

            int rowOffset = Adapter.ColumnOrdering.FirstDataRow;
            SetMaxColumnsCountByHeader(rowOffset);
            PublicServant currentServant = null;
            TI.Declarator.ParserCommon.Person currentPerson = null;

            int row = rowOffset;
            DeclarationSection currentSection = null;

            if (Adapter.ColumnOrdering.Section != null)
            {
                currentSection = new DeclarationSection() { Row = row, Name = Adapter.ColumnOrdering.Section };
                declaration.Sections.Add(currentSection);
            }
            for (row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                Row currRow = Adapter.GetRow(row);
                if (IAdapter.IsEmptyRow(currRow))
                {
                    continue;
                }
                // строка - разделитель
                string name;
                if (ColumnDetector.IsSection(currRow, out name))
                {
                    currentSection = new DeclarationSection() { Row = row, Name = name };
                    declaration.Sections.Add(currentSection);
                    currentServant = null;
                    if (currentPerson != null)
                    {
                        currentPerson.RangeHigh = row - 1;
                    }
                    currentPerson = null;
                    continue;
                }

                int merged_row_count = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).MergedRowsCount;

                string nameOrRelativeType = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).Text.CleanWhitespace();
                string occupationStr = "";
                if (Adapter.HasDeclarationField(DeclarationField.Occupation))
                {
                    occupationStr = Adapter.GetDeclarationField(row, DeclarationField.Occupation).Text;
                }

                if (String.IsNullOrWhiteSpace(nameOrRelativeType))
                {
                    if (currentPerson == null)
                    {
                        throw new SmartParserException(
                            string.Format("No Person  at row {0}", row));
                    }
                    continue;
                }
                if (DataHelper.IsPublicServantInfo(nameOrRelativeType))
                {
                    //Logger.Debug("{0} Servant {1} Occupation {2}", row, nameOrRelativeType, occupationStr);
                    if (currentPerson != null)
                    {
                        currentPerson.RangeHigh = row - 1;
                    }
                    currentServant = new PublicServant()
                    {
                        NameRaw = nameOrRelativeType,
                        Name = DataHelper.NormalizeName(nameOrRelativeType),
                        Occupation = occupationStr
                    };
                    if (currentSection != null)
                    {
                        currentServant.Department = currentSection.Name;
                    }

                    declaration.PublicServants.Add(currentServant);
                    currentPerson = currentServant;
                    currentPerson.RangeLow = row;

                }
                else if (DataHelper.IsRelativeInfo(nameOrRelativeType, occupationStr))
                {
                    if (currentServant == null)
                    {
                        // ошибка
                        throw new SmartParserException(
                            string.Format("Relative {0} at row {1} without main Person", nameOrRelativeType, row));
                    }
                    currentPerson.RangeHigh = row - 1;
                    Relative relative = new Relative();
                    currentServant.Relatives.Add(relative);
                    currentPerson = relative;
                    currentPerson.RangeLow = row;

                    RelationType relationType = DataHelper.ParseRelationType(nameOrRelativeType, false);
                    if (relationType == RelationType.Error)
                    {
                        throw new SmartParserException(
                            string.Format("Wrong relative name '{0}' at row {1} ", nameOrRelativeType, row));
                    }
                    relative.RelationType = relationType;


                    //Logger.Debug("{0} Relative {1} Relation {2}", row, nameOrRelativeType, relationType.ToString());
                }
                else
                {
                    // error
                    throw new SmartParserException(
                        string.Format("Wrong nameOrRelativeType {0} (occupation {2}) at row {1}", nameOrRelativeType, row, occupationStr));
                }
                if (merged_row_count > 1)
                {
                    row += merged_row_count - 1;
                }
            }
            if (currentPerson != null)
            {
                currentPerson.RangeHigh = row - 1;
            }


            Logger.Info("Parsed {0} declarants", declaration.PublicServants.Count());

            ParsePersonalProperties(declaration);

            return declaration;
        }

        public static void CheckProperty(RealEstateProperty prop)
        {
            if (prop == null)
            {
                return;
            }

            if (String.IsNullOrEmpty(prop.CountryStr))
            {
                Logger.Error(CurrentRow, "wrong country: {0}", prop.country_raw);
            }
            if (prop.OwnershipType == 0)
            {
                Logger.Error(CurrentRow, "wrong ownership type: {0}", prop.own_type_raw);
            }
            if (prop.PropertyType == 0)
            {
                Logger.Error(CurrentRow, "wrong property type: {0}", prop.type_raw);
            }
        }

        public void ParseOwnedProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.OwnedRealEstateArea))
            {
                // no square, no entry
                return;
            }
            string estateTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateType);
            string ownTypeStr = null;
            if (currRow.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                ownTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateOwnershipType);
            }
            string areaStr = currRow.GetContents(DeclarationField.OwnedRealEstateArea);
            string countryStr = currRow.GetContents(DeclarationField.OwnedRealEstateCountry);

            try
            {
                if (GetLinesStaringWithNumbers(areaStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, ownTypeStr, areaStr, countryStr, person);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, ownTypeStr, areaStr, countryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseMixedProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.MixedRealEstateArea))
            {
                // no square, no entry
                return;
            }
            string estateTypeStr = currRow.GetContents(DeclarationField.MixedRealEstateType);
            string areaStr = currRow.GetContents(DeclarationField.MixedRealEstateArea);
            string countryStr = currRow.GetContents(DeclarationField.MixedRealEstateCountry);

            try
            {
                if (GetLinesStaringWithNumbers(areaStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, null, areaStr, countryStr, person);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, null, areaStr, countryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseStateProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.StatePropertyArea))
            {
                // no square, no entry
                return;
            }
            string statePropTypeStr = currRow.GetContents(DeclarationField.StatePropertyType);
            string statePropAreaStr = currRow.GetContents(DeclarationField.StatePropertyArea);
            string statePropCountryStr = currRow.GetContents(DeclarationField.StatePropertyCountry);

            try
            {
                if (GetLinesStaringWithNumbers(statePropAreaStr).Count > 1)
                {
                    ParseStatePropertyManyValuesInOneCell(statePropTypeStr, statePropAreaStr, statePropCountryStr, person);
                }
                else
                {
                    ParseStatePropertySingleRow(statePropTypeStr, statePropAreaStr, statePropCountryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public Declaration ParsePersonalProperties(Declaration declaration)
        {
            SecondPassStartTime = DateTime.Now;
            int count = 0;
            int total_count = declaration.PublicServants.Count();

            foreach (PublicServant servant in declaration.PublicServants)
            {
                count++;
                if (count % 1000 == 0)
                {
                    double time_sec = DateTime.Now.Subtract(SecondPassStartTime).TotalSeconds;
                    Logger.Info("Done: {0:0.00}%", 100.0 * count / total_count);

                    Logger.Info("Rate: {0:0.00} declarant in second", count / time_sec );
                }
                List<Person> servantAndRel = new List<Person>() { servant };
                servantAndRel.AddRange(servant.Relatives);

                foreach (Person person in servantAndRel)
                {
                    bool foundIncomeInfo = false;
                    for (int row = person.RangeLow; row <= person.RangeHigh; row++)
                    {
                        CurrentRow = row;
                        Row currRow = Adapter.GetRow(row);
                        if (currRow == null || currRow.Cells.Count == 0)
                        {
                            continue;
                        }

                        if (!foundIncomeInfo)
                        {
                            string s = currRow.GetContents(DeclarationField.DeclaredYearlyIncome);
                            if (s != "")
                            {
                                person.DeclaredYearlyIncome = DataHelper.ParseDeclaredIncome(s);
                                totalIncome += person.DeclaredYearlyIncome == null ? 0 : person.DeclaredYearlyIncome.Value;
                                foundIncomeInfo = true;
                            }
                        }

                        ParseOwnedProperty(currRow, person);
                        ParseStateProperty(currRow, person);
                        ParseMixedProperty(currRow, person);

                        // Парсим транспортные средства
                        string vehicleStr = GetVehicleString(currRow); // r.GetContents(DeclarationField.Vehicle);
                        List<Vehicle> vehicles = new List<Vehicle>();
                        DataHelper.ParseVehicle(vehicleStr, vehicles);
                        person.Vehicles.AddRange(vehicles);
                    }
                }
            }

            Logger.Info("Total income: {0}", totalIncome);
            double seconds = DateTime.Now.Subtract(FirstPassStartTime).TotalSeconds;
            Logger.Info("Final Rate: {0:0.00} declarant in second", count / seconds);
            double total_seconds = DateTime.Now.Subtract(FirstPassStartTime).TotalSeconds;
            Logger.Info("Total time: {0:0.00} seconds", total_seconds);
            return declaration;
        }

        private string GetVehicleString(Row r)
        {
            string vehicle = "";
            if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.Vehicle))
            {
                vehicle = r.GetContents(DeclarationField.Vehicle);
            }
            else
            {
                vehicle = (r.GetContents(DeclarationField.VehicleType) + " " + r.GetContents(DeclarationField.VehicleModel)).Trim();
            }
            return Regex.Replace(vehicle, @"\s{2,}", " ");
        }

        static bool CheckEmptyValues(string propTypeStr)
        {
            propTypeStr = propTypeStr.Trim();
            if (string.IsNullOrWhiteSpace(propTypeStr) ||
                propTypeStr == "-" ||
                propTypeStr == "_" ||
                propTypeStr == "-\n-" ||
                propTypeStr == "не имеет")
            {
                return true;
            }
            return false;
        }

        static public void  ParseStatePropertySingleRow(string statePropTypeStr, string statePropAreaStr, string statePropCountryStr, Person person)
        {
            statePropTypeStr = statePropTypeStr.Trim();
            if (CheckEmptyValues(statePropTypeStr))
            {
                return;
            }
            RealEstateProperty stateProperty = new RealEstateProperty();


            var propertyType = DeclaratorApiPatterns.TryParseRealEstateType(statePropTypeStr);
            decimal? area = DataHelper.ParseArea(statePropAreaStr);
            Country country = DataHelper.TryParseCountry(statePropCountryStr);
            string countryStr = DeclaratorApiPatterns.TryParseCountry(statePropCountryStr);

            var combinedData = DataHelper.ParseCombinedRealEstateColumn(statePropTypeStr.CleanWhitespace(), OwnershipType.InUse);

            stateProperty.Text = statePropTypeStr;
            stateProperty.PropertyType = propertyType;
            stateProperty.type_raw = statePropTypeStr;
            stateProperty.Area = area;
            stateProperty.square_raw = statePropAreaStr;
            stateProperty.Country = country;
            stateProperty.CountryStr = countryStr;
            stateProperty.country_raw = statePropCountryStr;
            stateProperty.OwnershipType = combinedData.Item2;
            stateProperty.OwnedShare = combinedData.Item3;
            CheckProperty(stateProperty);
            person.RealEstateProperties.Add(stateProperty);
        }

        // 
        static public void ParseOwnedPropertySingleRow(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person)
        {
            estateTypeStr = estateTypeStr.Trim();
            areaStr = areaStr.CleanWhitespace();
            if (CheckEmptyValues(estateTypeStr))
            {
                return;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.Area = DataHelper.ParseArea(areaStr);
            realEstateProperty.square_raw = areaStr;

            realEstateProperty.CountryStr = DeclaratorApiPatterns.TryParseCountry(countryStr);//. DataHelper.TryParseCountry(countryStr);
            realEstateProperty.country_raw = countryStr;

            RealEstateType realEstateType = RealEstateType.Other;
            OwnershipType ownershipType = OwnershipType.Ownership;
            string share = "";

            // колонка с типом недвижимости отдельно
            if (ownTypeStr != null)
            {
                realEstateType = DataHelper.TryParseRealEstateType(estateTypeStr);
                ownershipType = DataHelper.TryParseOwnershipType(ownTypeStr, OwnershipType.Ownership);
                share = DataHelper.ParseOwnershipShare(ownTypeStr, ownershipType);

                realEstateProperty.PropertyType = realEstateType;
                realEstateProperty.OwnershipType = ownershipType;
                realEstateProperty.OwnedShare = share;

                realEstateProperty.type_raw = estateTypeStr;
                realEstateProperty.own_type_raw = ownTypeStr;
                realEstateProperty.share_amount_raw = ownTypeStr;
            }
            else // колонка содержит тип недвижимости и тип собственности
            {
                var combinedData = DataHelper.ParseCombinedRealEstateColumn(estateTypeStr.CleanWhitespace());
            
                realEstateType = combinedData.Item1;
                ownershipType = combinedData.Item2;
                share = combinedData.Item3;

                realEstateProperty.PropertyType = realEstateType;
                realEstateProperty.OwnershipType = ownershipType;
                realEstateProperty.OwnedShare = share;

                realEstateProperty.type_raw = estateTypeStr;

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
                if (Regex.Matches(lines[i], "^\\s*[0-9]").Count > 0)
                {
                    linesWithNumbers.Add(i);
                }
            }
            return linesWithNumbers;

        }

        static string SliceArrayAndTrim(string[] lines, int start, int end)
        {
            return  String.Join("\n", lines.Skip(start).Take(end - start)).CleanWhitespace();
        }

        static List<string> DivideByBordersOrEmptyLines(string value, List<int> borders)
        {
            var result = new List<string>();
            if (value == null)
            {
                return result;
            }
            string[] lines = value.Split('\n');
            Debug.Assert(borders.Count > 1);
            int startLine = borders[0];
            int borderIndex = 1;
            string item = "";
            for (int i = startLine + 1; i < lines.Count(); ++i)
            {
                item = SliceArrayAndTrim(lines, startLine, i);
                if (item.Count() > 0) // not empty item
                {
                    if ((borderIndex < borders.Count && i == borders[borderIndex]) || lines[i].Trim().Count() == 0)
                    {
                        result.Add(item);
                        startLine = i;
                        borderIndex++;
                    }
                }

            }
            item = SliceArrayAndTrim(lines, startLine, lines.Count());
            if (item.Count() > 0) result.Add(item);
            return result;
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

        static public void ParseOwnedPropertyManyValuesInOneCell(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person)
        {
            List<int> linesWithNumbers = GetLinesStaringWithNumbers(areaStr);
            List<string> estateTypes = DivideByBordersOrEmptyLines(estateTypeStr, linesWithNumbers);
            List<string> areas = DivideByBordersOrEmptyLines(areaStr, linesWithNumbers);
            List<string> ownTypes = DivideByBordersOrEmptyLines(ownTypeStr, linesWithNumbers);
            List<string> countries = DivideByBordersOrEmptyLines(countryStr, linesWithNumbers);
            for (int i=0; i < areas.Count; ++i )
            {
                ParseOwnedPropertySingleRow(
                    GetListValueOrDefault(estateTypes,i, ""), 
                    GetListValueOrDefault(ownTypes, i, null),
                    GetListValueOrDefault(areas, i, ""),
                    GetListValueOrDefault(countries, i, ""),
                    person
                );
            }
        }
        static public void ParseStatePropertyManyValuesInOneCell(string estateTypeStr, string areaStr, string countryStr, Person person)
        {
            List<int> linesWithNumbers = GetLinesStaringWithNumbers(areaStr);
            List<string> estateTypes = DivideByBordersOrEmptyLines(estateTypeStr, linesWithNumbers);
            List<string> areas = DivideByBordersOrEmptyLines(areaStr, linesWithNumbers);
            List<string> countries = DivideByBordersOrEmptyLines(countryStr, linesWithNumbers);
            for (int i = 0; i < areas.Count; ++i)
            {
                ParseStatePropertySingleRow(
                    GetListValueOrDefault(estateTypes, i, ""),
                    GetListValueOrDefault(areas, i, ""),
                    GetListValueOrDefault(countries, i, ""),
                    person
                );
            }
        }


        IAdapter Adapter { get; set; }
        static int CurrentRow { get; set;  } = -1;

        Decimal totalIncome = 0;
    }
}
