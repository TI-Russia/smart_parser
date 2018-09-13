using CsvHelper;
using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
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
            List<PublicServant> servants = new List<PublicServant>();
            PublicServant currentServant = null;
            TI.Declarator.ParserCommon.Person currentPerson = null;
            int rowOffset = Adapter.ColumnOrdering.FirstDataRow;

            for (int row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                string nameOrRelativeType = Adapter.GetDeclarationField(row, DeclarationField.NameOrRelativeType).Text.CleanWhitespace();
                string occupationStr = "";
                try
                {
                    occupationStr = Adapter.GetDeclarationField(row, DeclarationField.Occupation).Text;
                }
                catch (Exception)
                { }
                string declaredYearlyIncomeStr = Adapter.GetDeclarationField(row, DeclarationField.DeclaredYearlyIncome).Text;
                decimal? declaredYearlyIncome = DataHelper.ParseDeclaredIncome(declaredYearlyIncomeStr);

                if (DataHelper.IsPublicServantInfo(nameOrRelativeType))
                {
                    Logger.Info("{0} Servant {1} Occupation {2}", row, nameOrRelativeType, occupationStr);
                    PublicServant pServ = new PublicServant()
                    {
                        Name = nameOrRelativeType,
                        Occupation = occupationStr
                    };

                    currentServant = pServ;
                    currentPerson = pServ;
                    servants.Add(pServ);
                    currentPerson.DeclaredYearlyIncome = declaredYearlyIncome;
                }
                else if (DataHelper.IsRelativeInfo(nameOrRelativeType, occupationStr))
                {
                    RelationType relationType = DataHelper.ParseRelationType(nameOrRelativeType, false);

                    if (relationType == RelationType.Error)
                    {
                        Logger.Error("***ERROR row({0}) unknown relation type {1}", row, nameOrRelativeType);
                        continue;
                    }
                    Relative pRel = new Relative()
                    {
                        RelationType = relationType
                    };


                    Logger.Info("{0} Relative {1} Relation {2}", row, nameOrRelativeType, relationType.ToString());

                    currentServant.Relatives.Add(pRel);
                    currentPerson = pRel;
                    currentPerson.DeclaredYearlyIncome = declaredYearlyIncome;
                }

                if (currentPerson == null)
                {
                    Logger.Error("***ERROR No current person({0})", row);
                    continue;
                }

                try
                {
                    FillPersonProperties(Adapter.Rows[row], currentPerson);
                }
                catch (Exception e)
                {
                    Logger.Error("***ERROR row({0}) {1}", row, e.Message);
                    continue;
                }

            }

            return new Declaration()
            {
                Declarants = servants,
                Properties = new DeclarationProperties() { Title = "title", Year = 2010, MinistryName = "Ministry" }
            };

        }

        private PublicServant ParsePublicServantInfo(Row r)
        {
            string occ = r.GetContents(DeclarationField.Occupation);
            var res = new PublicServant()
            {
                Name = r.GetContents(DeclarationField.NameOrRelativeType),
                Occupation = occ
            };

            FillPersonProperties(r, res);

            return res;
        }
        private Relative ParseRelativeInfo(Row r)
        {
            var res = new Relative()
            {
                RelationType = DataHelper.ParseRelationType(r.GetContents(DeclarationField.NameOrRelativeType))
            };

            FillPersonProperties(r, res);

            return res;
        }

        private string GetVehicleString(Row r)
        {
            if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.Vehicle))
            {
                return r.GetContents(DeclarationField.Vehicle);
            }
            return (r.GetContents(DeclarationField.VehicleType) + " " + r.GetContents(DeclarationField.VehicleModel)).Trim();
        }

        private void FillPersonProperties(Row r, Person p)
        {
            var ownedProperty = ParseOwnedProperty(r);
            if (ownedProperty != null && ownedProperty.Count() > 0)
            {
                p.RealEstateProperties.AddRange(ownedProperty);
            }

            var stateProperty = ParseStateProperty(r);
            if (stateProperty != null && stateProperty.Count() > 0)
            {
                p.RealEstateProperties.AddRange(stateProperty);
            }

            string vehicle = GetVehicleString(r); // r.GetContents(DeclarationField.Vehicle);
            if (!String.IsNullOrEmpty(vehicle) && vehicle.Trim() != "-")
            {
                p.Vehicles.Add(vehicle);
            }

            if (r.ColumnOrdering[DeclarationField.DataSources] != null)
            {
                p.DataSources = DataHelper.ParseDataSources(r.GetContents(DeclarationField.DataSources));
            }
        }

        private IEnumerable<RealEstateProperty> ParseOwnedProperty(Row r)
        {
            IEnumerable<RealEstateType> propertyTypes;
            IEnumerable<OwnershipType> ownershipTypes;
            IEnumerable<string> shares;
            string estateTypeStr = r.GetContents(DeclarationField.OwnedRealEstateType);
            if (String.IsNullOrWhiteSpace(estateTypeStr) || estateTypeStr.Trim() == "-")
            {
                return null;
            }

            if (r.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                propertyTypes = DataHelper.ParseRealEstateTypes(estateTypeStr);
                ownershipTypes = DataHelper.ParseOwnershipTypes(r.GetContents(DeclarationField.OwnedRealEstateOwnershipType));
                shares = DataHelper.ParseOwnershipShares(r.GetContents(DeclarationField.OwnedRealEstateOwnershipType), ownershipTypes);
            }
            else
            {
                var combinedData = DataHelper.ParsePropertyAndOwnershipTypes(estateTypeStr.CleanWhitespace());

                propertyTypes = combinedData.Select(tup => tup.Item1);
                ownershipTypes = combinedData.Select(tup => tup.Item2);
                shares = combinedData.Select(tup => tup.Item3);
            }

            decimal? area;
            string areaStr = r.GetContents(DeclarationField.OwnedRealEstateArea).CleanWhitespace();
            IEnumerable<decimal?> areas = DataHelper.ParseAreas(areaStr);

            IEnumerable<Country> countries = DataHelper.ParseCountries(r.GetContents(DeclarationField.OwnedRealEstateCountry));

            var res = new List<RealEstateProperty>();

            for (int i = 0; i < propertyTypes.Count(); i++)
            {
                res.Add(new RealEstateProperty(ownershipTypes.ElementAt(i), propertyTypes.ElementAt(i), countries.ElementAtOrDefault(i), areas.ElementAt(i), estateTypeStr, shares.ElementAt(i)));
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
                res.Add(new RealEstateProperty(ownershipType, propertyTypes.ElementAt(i), countries.ElementAt(i), areas.ElementAt(i), propTypeStr, share));
            }

            return res;
        }



        IAdapter Adapter { get; set; }

        List<Tuple<int, int>> personBounds = new List<Tuple<int, int>>();
        List<Tuple<int, int>> organsBounds = new List<Tuple<int, int>>();
        List<int> headerPositions = new List<int>();
        List<Organization> organizations = new List<Organization>();
        List<Tuple<string, Tuple<int, int>>> organsBoundsList = new List<Tuple<string, Tuple<int, int>>>();
        List<Person> organPersons = new List<Person>();

        List<string> relationTypes = new List<string>();

        Dictionary<string, int> ownershipTypes = new Dictionary<string, int>();
        Dictionary<string, int> objectTypes = new Dictionary<string, int>();

    }
}
