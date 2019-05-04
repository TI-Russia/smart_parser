using CsvHelper;
using Parser.Lib;
using Smart.Parser.Adapters;
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

        public Declaration Parse()
        {
            Declaration declaration = new Declaration()
            {
                Properties = new DeclarationProperties() { Title = "title", Year = 2018, MinistryName = "Ministry" }
            };
            totalIncome = 0;

            int rowOffset = Adapter.ColumnOrdering.FirstDataRow;
            PublicServant currentServant = null;
            TI.Declarator.ParserCommon.Person currentPerson = null;
            int merged_col_count = 0;

            int row = rowOffset;
            for (row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                // строка - разделитель
                if (Adapter.GetCell(row, 0).MergedColsCount > 1)
                {
                    string name = Adapter.GetCell(row, 0).Text;
                    if (name.Length > 5)
                    {
                        declaration.Sections.Add(new DeclarationSection() { Row = row, Name = name });
                        continue;
                    }
                }

                merged_col_count = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).MergedColsCount;

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
                if (merged_col_count > 1)
                {
                    row += merged_col_count - 1;
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

        public void CheckProperty(RealEstateProperty prop)
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



        public Declaration ParsePersonalProperties(Declaration declaration)
        {
            foreach (PublicServant servant in declaration.PublicServants)
            {
                List<Person> servantAndRel = new List<Person>() { servant };
                servantAndRel.AddRange(servant.Relatives);

                foreach (Person person in servantAndRel)
                {
                    bool firstRow = true;
                    for (int row = person.RangeLow; row <= person.RangeHigh; row++)
                    {
                        CurrentRow = row;
                        Row r = Adapter.GetRow(row);

                        if (firstRow)
                        {
                            // парсим доход
                            string declaredYearlyIncomeStr = Adapter.GetDeclarationField(row, DeclarationField.DeclaredYearlyIncome).Text;
                            decimal? declaredYearlyIncome = null;
                            try
                            {
                                declaredYearlyIncome = DataHelper.ParseDeclaredIncome(declaredYearlyIncomeStr);
                            }
                            catch (Exception e)
                            {
                                Logger.Error("***ERROR row({0}) wrong income: {1}", row, e.Message);
                            }
                            person.DeclaredYearlyIncome = declaredYearlyIncome;
                            totalIncome += declaredYearlyIncome == null ? 0 : declaredYearlyIncome.Value;
                            firstRow = false;
                        }


                        // Парсим недвижимость в собственности
                        string estateTypeStr = r.GetContents(DeclarationField.OwnedRealEstateType);
                        string ownTypeStr = null;
                        if (r.ColumnOrdering.OwnershipTypeInSeparateField)
                        {
                            ownTypeStr = r.GetContents(DeclarationField.OwnedRealEstateOwnershipType);
                        }
                        string areaStr = r.GetContents(DeclarationField.OwnedRealEstateArea).CleanWhitespace();
                        string countryStr = r.GetContents(DeclarationField.OwnedRealEstateCountry);

                        RealEstateProperty ownedProperty = null;

                        try
                        {
                            ownedProperty = ParseOwnedProperty(estateTypeStr, ownTypeStr, areaStr, countryStr);
                        }
                        catch (Exception e)
                        {
                            Logger.Error("***ERROR row({0}) {1}", row, e.Message);
                        }

                        if (ownedProperty != null)
                        {
                            CheckProperty(ownedProperty);
                            person.RealEstateProperties.Add(ownedProperty);
                        }

                        // Парсим недвижимость в пользовании
                        string statePropTypeStr = r.GetContents(DeclarationField.StatePropertyType);
                        string statePropAreaStr = r.GetContents(DeclarationField.StatePropertyArea);
                        string statePropCountryStr = r.GetContents(DeclarationField.StatePropertyCountry);

                        RealEstateProperty stateProperty = null;
                        try
                        {
                            stateProperty = ParseStateProperty(statePropTypeStr, statePropAreaStr, statePropCountryStr);
                        }
                        catch (Exception e)
                        {
                            Logger.Error("***ERROR row({0}) {1}", row, e.Message);
                        }
                        CheckProperty(stateProperty);

                        if (stateProperty != null)
                        {
                            person.RealEstateProperties.Add(stateProperty);
                        }

                        // Парсим транспортные средства
                        string vehicleStr = GetVehicleString(Adapter.GetRow(row)); // r.GetContents(DeclarationField.Vehicle);
                        List<Vehicle> vehicles = new List<Vehicle>();
                        DataHelper.ParseVehicle(vehicleStr, vehicles);
                        person.Vehicles.AddRange(vehicles);
                    }
                }
            }

            Logger.Info("Total income: {0}", totalIncome);
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

        static public RealEstateProperty ParseStateProperty(string statePropTypeStr, string statePropAreaStr, string statePropCountryStr)
        {
            statePropTypeStr = statePropTypeStr.Trim();
            if (string.IsNullOrWhiteSpace(statePropTypeStr) || 
                statePropTypeStr == "-" ||
                statePropTypeStr == "_" ||
                statePropTypeStr == "-\n-" || 
                statePropTypeStr == "не имеет")
            {
                return null;
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


            return stateProperty;
        }

        // 
        static public RealEstateProperty ParseOwnedProperty(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr)
        {
            estateTypeStr = estateTypeStr.Trim();
            if (String.IsNullOrWhiteSpace(estateTypeStr) || 
                estateTypeStr.Trim() == "-" ||
                estateTypeStr.Trim() == "_" ||
                estateTypeStr == "не имеет")
            {
                return null;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.Area = DataHelper.ParseArea(areaStr);
            realEstateProperty.square_raw = areaStr;

            //realEstateProperty.Country = DataHelper.TryParseCountry(countryStr);
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
                //static public Tuple<RealEstateType, OwnershipType, string> ParseStatePropertyTypeColumn(string strPropInfo)

                realEstateType = combinedData.Item1;
                ownershipType = combinedData.Item2;
                share = combinedData.Item3;

                realEstateProperty.PropertyType = realEstateType;
                realEstateProperty.OwnershipType = ownershipType;
                realEstateProperty.OwnedShare = share;

                realEstateProperty.type_raw = estateTypeStr;
                //realEstateProperty.own_type_raw = estateTypeStr;
                //realEstateProperty.share_amount_raw = estateTypeStr;

            }

            realEstateProperty.Text = estateTypeStr;
            return realEstateProperty;
        }
        /*
        public List<RealEstateProperty> ParseOwnedProperty(IAdapter adapter, int firstRow, int lastRow)
        {
            for (int row = firstRow; row < lastRow; row++)
            {
                var cell = adapter.GetDeclarationField(row, DeclarationField.OwnedRealEstateType);

                string estateTypeStr = cell.GetText(true);
                if (String.IsNullOrWhiteSpace(estateTypeStr) || estateTypeStr.Trim() == "-")
                {
                    return null;
                }

                if (adapter.ColumnOrdering.OwnershipTypeInSeparateField)
                {
                    // колонка с типом недвижимости отдельно
                }
                else // колонка содержит тип недвижимости и тип собственности
                {
                    var combinedData = DataHelper.ParsePropertyAndOwnershipTypes(estateTypeStr.CleanWhitespace());

                    //propertyTypes = combinedData.Select(tup => tup.Item1).ToList();
                    //ownershipTypes = combinedData.Select(tup => tup.Item2).ToList();
                    //shares = combinedData.Select(tup => tup.Item3).ToList();
                }


                string areaStr = adapter.GetContents(row, DeclarationField.OwnedRealEstateArea).CleanWhitespace();
                decimal? area = DataHelper.ParseArea(areaStr);

                Country country = DataHelper.ParseCountry(adapter.GetContents(row, DeclarationField.OwnedRealEstateCountry));

                if (cell.MergedRowsCount > 1)
                    row += cell.MergedRowsCount - 1;
            }

            return null;
        }
        */
        // парсинг недвижимости, находящейся в собственности, вычисляется share_type

        // используются колонки OwnedRealEstateType
        // OwnershipTypeInSeparateField
        // OwnedRealEstateOwnershipType
        // OwnedRealEstateArea
        // OwnedRealEstateCountry
        // 
#if false

        private List<RealEstateProperty> ParseOwnedProperty(Row r)
        {
            List<RealEstateType> propertyTypes;
            List<OwnershipType> ownershipTypes;
            List<string> shares;
            string estateTypeStr = r.GetContents(DeclarationField.OwnedRealEstateType);
            if (String.IsNullOrWhiteSpace(estateTypeStr) || estateTypeStr.Trim() == "-")
            {
                return null;
            }

            // колонка с типом недвижимости отдельно
            if (r.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                propertyTypes = DataHelper.ParseRealEstateTypes(estateTypeStr).ToList();
                string ownershipStr = r.GetContents(DeclarationField.OwnedRealEstateOwnershipType);
                ownershipTypes = DataHelper.ParseOwnershipTypes(ownershipStr).ToList();
                shares = DataHelper.ParseOwnershipShares(ownershipStr, ownershipTypes).ToList();
            }
            else // колонка содержит тип недвижимости и тип собственности
            {
                var combinedData = DataHelper.ParsePropertyAndOwnershipTypes(estateTypeStr.CleanWhitespace());

                propertyTypes = combinedData.Select(tup => tup.Item1).ToList();
                ownershipTypes = combinedData.Select(tup => tup.Item2).ToList();
                shares = combinedData.Select(tup => tup.Item3).ToList();
            }

            decimal? area;
            string areaStr = r.GetContents(DeclarationField.OwnedRealEstateArea).CleanWhitespace();
            List<decimal?> areas = DataHelper.ParseAreas(areaStr).ToList();

            List<Country> countries = DataHelper.ParseCountries(r.GetContents(DeclarationField.OwnedRealEstateCountry)).ToList();

            var res = new List<RealEstateProperty>();

            // TBD: check all array have same size
            for (int i = 0; i < propertyTypes.Count(); i++)
            {
                res.Add(new RealEstateProperty(
                    ownershipTypes.ElementAt(i),
                    propertyTypes.ElementAt(i),
                    countries.ElementAtOrDefault(i),
                    areas.ElementAtOrDefault(i),
                    estateTypeStr,
                    shares.ElementAt(i)));
            }
            return res;
        }
        private IEnumerable<RealEstateProperty> ParseStateProperty(Row r)
        {
            IEnumerable<RealEstateType> propertyTypes;
            string propTypeStr = r.GetContents(DeclarationField.StatePropertyType);
            if (string.IsNullOrWhiteSpace(propTypeStr) || propTypeStr.Trim() == "-" || propTypeStr.Trim() == "-\n-") return null;

            if (r.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                propertyTypes = DataHelper.ParseRealEstateTypes(propTypeStr);
            }
            else
            {
                propertyTypes = DataHelper.ParseStatePropertyTypesWithUsageInfo(propTypeStr.Replace("\\0", ")"));
            }


            OwnershipType ownershipType = OwnershipType.NotAnOwner;
            string share = "";
            string areaStr = r.GetContents(DeclarationField.StatePropertyArea).Trim();
            IEnumerable<decimal?> areas = DataHelper.ParseAreas(areaStr);


            IEnumerable<Country> countries = DataHelper.ParseCountries(r.GetContents(DeclarationField.StatePropertyCountry));

            var res = new List<RealEstateProperty>();
            for (int i = 0; i < propertyTypes.Count(); i++)
            {
                decimal? area = null;
                if (areas.Count() > i)
                {
                    area = areas.ElementAt(i);
                }
                res.Add(new RealEstateProperty(ownershipType, propertyTypes.ElementAt(i), countries.ElementAt(i), area, propTypeStr, share));
            }

            return res;
        }
#endif



        IAdapter Adapter { get; set; }
        static int CurrentRow { get; set;  } = -1;

        List<Tuple<int, int>> personBounds = new List<Tuple<int, int>>();
        List<Tuple<int, int>> organsBounds = new List<Tuple<int, int>>();
        List<int> headerPositions = new List<int>();
        List<Organization> organizations = new List<Organization>();
        List<Tuple<string, Tuple<int, int>>> organsBoundsList = new List<Tuple<string, Tuple<int, int>>>();
        List<Person> organPersons = new List<Person>();

        List<string> relationTypes = new List<string>();

        Dictionary<string, int> ownershipTypes = new Dictionary<string, int>();
        Dictionary<string, int> objectTypes = new Dictionary<string, int>();

        Decimal totalIncome = 0;

    }
}
