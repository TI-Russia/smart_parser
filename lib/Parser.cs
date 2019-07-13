using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    public class Parser
    {
        DateTime FirstPassStartTime;
        DateTime SecondPassStartTime;
        bool FailOnRelativeOrphan;

        public int NameOrRelativeTypeColumn { set; get; } = 1;

        public Parser(IAdapter adapter, bool failOnRelativeOrphan=true)
        {
            Adapter = adapter;
            FailOnRelativeOrphan = failOnRelativeOrphan;
        }

        Declaration InitializeDeclaration()
        {
            // parse filename
            int? id;
            string archive;
            bool result = DataHelper.ParseDocumentFileName(Adapter.DocumentFile, out id, out archive);

            DeclarationProperties properties = new DeclarationProperties()
            {
                Title = Adapter.ColumnOrdering.Title,
                MinistryName = Adapter.ColumnOrdering.MinistryName,
                Year = Adapter.ColumnOrdering.Year,
                SheetName = Adapter.GetWorksheetName(),
                documentfile_id = id,
                archive_file = archive,
                sheet_number = Adapter.GetWorksheetIndex()
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
            return declaration;
        }

        TI.Declarator.ParserCommon.Person CreateNewRelative(int row, string relativeStr,
            PublicServant currentServant, 
            TI.Declarator.ParserCommon.Person currentPerson,
            string documentPosition)
        {
            Logger.Debug("Relative {0} at row {1}", relativeStr, row);
            if (currentServant == null)
            {
                if (FailOnRelativeOrphan) {
                    throw new SmartParserException(
                        string.Format("Relative {0} at row {1} without main Person", relativeStr, row));
                }
                else {
                    return null;
                }
            }
            currentPerson.RangeHigh = row - 1;
            Relative relative = new Relative();
            currentServant.Relatives.Add(relative);
            currentPerson = relative;
            currentPerson.RangeLow = row;

            RelationType relationType = DataHelper.ParseRelationType(relativeStr, false);
            if (relationType == RelationType.Error)
            {
                throw new SmartParserException(
                    string.Format("Wrong relative name '{0}' at row {1} ", relativeStr, row));
            }
            relative.RelationType = relationType;
            //Logger.Debug("{0} Relative {1} Relation {2}", row, nameOrRelativeType, relationType.ToString());
            relative.document_position = documentPosition;
            return currentPerson;
        }

        PublicServant CreateNewServant(int row, string fioStr, string occupationStr, 
            DeclarationSection currentSection, PublicServant currentServant, 
            ref TI.Declarator.ParserCommon.Person currentPerson,
            string documentPosition, int? index)
        {
            Logger.Debug("Declarant {0} at row {1}", fioStr, row);
            if (currentPerson != null)
            {
                currentPerson.RangeHigh = row - 1;
            }
            currentServant = new PublicServant()
            {
                NameRaw = fioStr,
                Occupation = occupationStr
            };
            if (currentSection != null)
            {
                currentServant.Department = currentSection.Name;
            }

            currentServant.Index = index;

            currentPerson = currentServant;
            currentPerson.RangeLow = row;
            currentPerson.document_position = documentPosition;
            

            return currentServant;
        }
        DeclarationSection CreateNewSection(int row, string sectionTitle,
            ref PublicServant currentServant,
            ref TI.Declarator.ParserCommon.Person currentPerson)
        {
            DeclarationSection currentSection = new DeclarationSection() { Row = row, Name = sectionTitle };
            Logger.Debug(String.Format("find section at line {0}:'{1}'", row, sectionTitle));
            currentServant = null;
            if (currentPerson != null)
            {
                currentPerson.RangeHigh = row - 1;
            }
            currentPerson = null;
            return currentSection;
        }

        int FindNextPersonIndex(int row, int mergedRowCount)
        {
            if (Adapter.HasDeclarationField(DeclarationField.RelativeTypeStrict))
            {
                for (int i = row + 1; i < row + mergedRowCount; i++)
                {
                    string text = Adapter.GetDeclarationField(i, DeclarationField.RelativeTypeStrict).Text;
                    if (text.CleanWhitespace() != "")
                    {
                        return i;
                    }
                }
            }
            return row + mergedRowCount;
        }

        public Declaration Parse()
        {
            FirstPassStartTime = DateTime.Now;

            Declaration declaration =  InitializeDeclaration();

            int rowOffset = Adapter.ColumnOrdering.FirstDataRow;
            Adapter.SetMaxColumnsCountByHeader(rowOffset);

            DeclarationSection currentSection = null;
            PublicServant currentServant = null;
            TI.Declarator.ParserCommon.Person currentPerson = null;
            
            if (Adapter.ColumnOrdering.Section != null)
            {
                currentSection = CreateNewSection(rowOffset, Adapter.ColumnOrdering.Section, ref currentServant, ref currentPerson);
                declaration.Sections.Add(currentSection);
            }
            for (int row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                Row currRow = Adapter.GetRow(row);
                if (currRow == null || currRow.IsEmpty())
                {
                    continue;
                }

                string sectionName;
                if (Adapter.IsSectionRow(currRow, out sectionName))
                {
                    currentSection = CreateNewSection(row, sectionName, ref currentServant, ref currentPerson);
                    declaration.Sections.Add(currentSection);
                    continue;
                }

                int mergedRowCount = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).MergedRowsCount;

                string nameOrRelativeType = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).Text.CleanWhitespace();
                string documentPosition = Adapter.GetDocumentPosition(row, DeclarationField.NameOrRelativeType);
                string relativeType = "";
                if  (DataHelper.IsEmptyValue(nameOrRelativeType) &&  Adapter.HasDeclarationField(DeclarationField.RelativeTypeStrict))
                {
                    relativeType = Adapter.GetDeclarationField(row, DeclarationField.RelativeTypeStrict).Text.CleanWhitespace();
                }
                
                string occupationStr = "";
                if (Adapter.HasDeclarationField(DeclarationField.Occupation))
                {
                    occupationStr = Adapter.GetDeclarationField(row, DeclarationField.Occupation).Text;
                }

                if (DataHelper.IsEmptyValue(nameOrRelativeType) && DataHelper.IsEmptyValue(relativeType))
                {
                    if (currentPerson == null)
                    {
                        if (FailOnRelativeOrphan)
                        {
                            throw new SmartParserException(
                                string.Format("No Person  at row {0}", row));
                        }
                    }
                    else
                    {
                        currentPerson.RangeHigh = row + mergedRowCount - 1; //see MinSevKavkaz2015_s.docx  in regression tests
                    }
                }
                else if (DataHelper.IsPublicServantInfo(nameOrRelativeType))
                {
                    int? index = null;
                    if (Adapter.HasDeclarationField(DeclarationField.Number))
                    {
                        string indexStr = Adapter.GetDeclarationField(row, DeclarationField.Number).Text
                            .Replace(".", "").CleanWhitespace();
                        int indVal;
                        bool dummyRes = Int32.TryParse(indexStr, out indVal);
                        if (dummyRes)
                        {
                            index = indVal;
                        }
                    }

                    currentServant = CreateNewServant(row, nameOrRelativeType, occupationStr,
                        currentSection, currentServant, ref currentPerson,
                        documentPosition, index);
                    declaration.PublicServants.Add(currentServant);
                }
                else
                {
                    if (DataHelper.IsEmptyValue(relativeType))
                        relativeType = nameOrRelativeType;
                    if (DataHelper.IsRelativeInfo(relativeType, occupationStr))
                    {
                        currentPerson = CreateNewRelative(row, relativeType, currentServant, currentPerson, documentPosition);
                    }
                    else
                    {
                        // error
                        throw new SmartParserException(
                            string.Format("Wrong nameOrRelativeType {0} (occupation {2}) at row {1}", nameOrRelativeType, row, occupationStr));
                    }
                }
                if (mergedRowCount > 1)
                {
                    row = FindNextPersonIndex(row, mergedRowCount) - 1; // we are in for cycle
                }
            }
            if (currentPerson != null)
            {
                currentPerson.RangeHigh = Adapter.GetRowsCount() - 1;
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

            if (String.IsNullOrEmpty(prop.country_raw))
            {
                Logger.Error(CurrentRow, "wrong country: {0}", prop.country_raw);
            }
        }

        public void ParseOwnedProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.OwnedRealEstateSquare))
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
            string squareStr = currRow.GetContents(DeclarationField.OwnedRealEstateSquare);
            string countryStr = currRow.GetContents(DeclarationField.OwnedRealEstateCountry);

            try
            {
                if (GetLinesStaringWithNumbers(squareStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, ownTypeStr, squareStr, countryStr, person);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, ownTypeStr, squareStr, countryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseMixedProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.MixedRealEstateSquare))
            {
                // no square, no entry
                return;
            }
            string estateTypeStr = currRow.GetContents(DeclarationField.MixedRealEstateType);
            string squareStr = currRow.GetContents(DeclarationField.MixedRealEstateSquare);
            string countryStr = currRow.GetContents(DeclarationField.MixedRealEstateCountry);

            try
            {
                if (GetLinesStaringWithNumbers(squareStr).Count > 1)
                {
                    ParseOwnedPropertyManyValuesInOneCell(estateTypeStr, null, squareStr, countryStr, person);
                }
                else
                {
                    ParseOwnedPropertySingleRow(estateTypeStr, null, squareStr, countryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }

        public void ParseStateProperty(Row currRow, Person person)
        {
            if (!Adapter.HasDeclarationField(DeclarationField.StatePropertySquare))
            {
                // no square, no entry
                return;
            }
            string statePropTypeStr = currRow.GetContents(DeclarationField.StatePropertyType);
            string statePropSquareStr = currRow.GetContents(DeclarationField.StatePropertySquare);
            string statePropCountryStr = currRow.GetContents(DeclarationField.StatePropertyCountry);

            try
            {
                if (GetLinesStaringWithNumbers(statePropSquareStr).Count > 1)
                {
                    ParseStatePropertyManyValuesInOneCell(statePropTypeStr, statePropSquareStr, statePropCountryStr, person);
                }
                else
                {
                    ParseStatePropertySingleRow(statePropTypeStr, statePropSquareStr, statePropCountryStr, person);
                }
            }
            catch (Exception e)
            {
                Logger.Error("***ERROR row({0}) {1}", currRow.Cells[0].Row, e.Message);
            }

        }
        bool ParseIncome(Row currRow, Person person)
        {
            if (Adapter.HasDeclarationField(DeclarationField.DeclaredYearlyIncomeThousands))
            {

                string s1 = currRow.GetContents(DeclarationField.DeclaredYearlyIncomeThousands);
                if (s1 != "")
                {
                    person.DeclaredYearlyIncome = DataHelper.ParseDeclaredIncome(s1) * 1000;
                    return true;
                }
                else
                {
                    return false;
                }
            }
            string s2 = currRow.GetContents(DeclarationField.DeclaredYearlyIncome);
            if (s2 != "")
            {
                person.DeclaredYearlyIncome = DataHelper.ParseDeclaredIncome(s2);
                return true;
            }
            return false;
        }

        public Declaration ParsePersonalProperties(Declaration declaration)
        {
            SecondPassStartTime = DateTime.Now;
            int count = 0;
            int total_count = declaration.PublicServants.Count();
            Decimal totalIncome = 0;

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
                    if (person is PublicServant)
                    {
                        Logger.Debug(((PublicServant)person).NameRaw.CleanWhitespace());
                    }
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
                            if (ParseIncome(currRow, person))
                            {
                                totalIncome += person.DeclaredYearlyIncome == null ? 0 : person.DeclaredYearlyIncome.Value;
                                foundIncomeInfo = true;
                            }
                        }

                        ParseOwnedProperty(currRow, person);
                        ParseStateProperty(currRow, person);
                        ParseMixedProperty(currRow, person);

                        AddVehicle(currRow, person); 
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

        private void AddVehicle(Row r, Person person)
        {
            if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.Vehicle))
            {
                var s = r.GetContents(DeclarationField.Vehicle);
                if (!DataHelper.IsEmptyValue(s))
                    person.Vehicles.Add(new Vehicle(s));
            }
            else
            {
                var m = r.GetContents(DeclarationField.VehicleModel);
                var t = r.GetContents(DeclarationField.VehicleType);
                if (!DataHelper.IsEmptyValue(m) || !DataHelper.IsEmptyValue(t))
                    person.Vehicles.Add(new Vehicle(m, t));
            }
        }

        static public void ParseStatePropertySingleRow(string statePropTypeStr, string statePropSquareStr, string statePropCountryStr, Person person)
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
            stateProperty.square_raw = statePropSquareStr;
            stateProperty.country_raw = statePropCountryStr;
            stateProperty.own_type_by_column = "В пользовании";
            CheckProperty(stateProperty);
            person.RealEstateProperties.Add(stateProperty);
        }

        static public void ParseOwnedPropertySingleRow(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person)
        {
            estateTypeStr = estateTypeStr.Trim();
            areaStr = areaStr.CleanWhitespace();
            if (DataHelper.IsEmptyValue(estateTypeStr))
            {
                return;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.square = DataHelper.ParseSquare(areaStr);
            realEstateProperty.square_raw = areaStr;
            realEstateProperty.country_raw = countryStr;

            // колонка с типом недвижимости отдельно
            if (ownTypeStr != null)
            {
                realEstateProperty.type_raw = estateTypeStr;
                realEstateProperty.own_type_raw = ownTypeStr;
                realEstateProperty.own_type_by_column = "В собственности";
                realEstateProperty.Text = estateTypeStr;
            }
            else // колонка содержит тип недвижимости и тип собственности
            {
                realEstateProperty.Text  = estateTypeStr;
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

        
    }
}
