using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Xml.Linq;

using TI.Declarator.ParserCommon;
using Xceed.Words.NET;

namespace TI.Declarator.WordParser
{
    public class DocXParser : IDeclarationParser
    {
        private static readonly XNamespace WordXNamespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

        private DeclarationProperties DeclarationProperties;
        private Dictionary<string, RealEstateType> PropertyTypes;

        public DocXParser(Dictionary<string, RealEstateType> propertyTypes)
        {
            this.PropertyTypes = propertyTypes;
        }


        public Declaration Parse(string filepath)
        {
            DocX doc = DocX.Load(filepath);
            DeclarationProperties = Scan(filepath);

            return Parse(doc);
        }

        public DeclarationProperties Scan(string filepath)
        {
            DocX doc = DocX.Load(filepath);
            string title = GetTitle(doc);
            var leadTable = doc.Tables.First();

            string fileName = Path.GetFileName(filepath);
            int? year = fileName.ExtractYear();
            if (!year.HasValue) year = title.ExtractYear();
            ColumnOrdering ordering = ExamineHeader(leadTable);

            return new DeclarationProperties()
            {
                ColumnOrdering = ordering,
                Year = year,
                Title = title
            };
        }

        public ColumnOrdering ExamineHeader(Table t)
        {
            int headerRowNum = 0;

            while (!IsHeader(t.Rows[headerRowNum]))
            {
                headerRowNum++;
            }

            var header = t.Rows[headerRowNum];

            ColumnOrdering res = new ColumnOrdering();
            int colCount = 0;
            int index = 0;
            foreach (var cell in header.Cells)
            {
                string text = cell.GetText(true);

                DeclarationField field;
                if (cell.GridSpan <= 1)
                {
                    if (!text.IsNullOrWhiteSpace())
                    {
                        field = HeaderHelpers.GetField(text.Replace('\n', ' '));
                        res.Add(field, index);
                        index++;
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header PROBABLY occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    int span = cell.GridSpan == 0 ? 1 : cell.GridSpan;
                    Row auxRow = t.Rows[headerRowNum + 1];
                    var auxCellsIter = auxRow.Cells.GetEnumerator();
                    auxCellsIter.MoveNext();
                    int auxColCount = 0;

                    while (auxColCount < colCount + span)
                    {
                        var auxCell = auxCellsIter.Current;
                        if (auxColCount >= colCount)
                        {
                            string fullText = text + " " + auxCell.GetText(true);
                            field = HeaderHelpers.GetField(fullText);
                            res.Add(field, index);
                            index++;
                        }

                        auxCellsIter.MoveNext();
                        int auxSpan = auxCell.GridSpan == 0 ? 1 : auxCell.GridSpan;
                        auxColCount += auxSpan;
                    }

                    colCount += cell.GridSpan;
                }

            }

            return res;
        }

        private string GetTitle(DocX doc)
        {
            var docBody = doc.Xml.Elements(WordXNamespace + "body");
            var titleParagraphs = doc.Xml.Elements().TakeWhile(el => el.Name.ToString() != $"{{{WordXNamespace}}}tbl");

            return titleParagraphs.Select(p => p.Value)
                                  .Aggregate("", (str1, str2) => str1 + '\n' + str2);
        }

        private bool IsHeader(Row r)
        {
            return (r.Cells.Count > 2) &&
                   (r.Cells.First().GetText(true) != "1");
        }

        private Declaration Parse(DocX doc, int rowOffset = 1)
        {
            var leadTable = doc.Tables.First();
            var servants = new List<PublicServant>();
            PublicServant currentServant = null;
            Person currentPerson = null;
            foreach (Row r in leadTable.Rows.Skip(rowOffset))
            {
                if (IsPublicServantInfo(r))
                {
                    PublicServant pServ = ParsePublicServantInfo(r);
                    currentServant = pServ;
                    currentPerson = pServ;

                    servants.Add(pServ);
                }
                else if (IsRelativeInfo(r))
                {
                    Relative pRel = ParseRelativeInfo(r);
                    currentServant.Relatives.Add(pRel);
                    currentPerson = pRel;
                }
            }

            return new Declaration()
            {
                Declarants = servants,
                Properties = DeclarationProperties
            };
        }

        private bool IsPublicServantInfo(Row r)
        {
            string nameOrRelativeType = GetContents(r, DeclarationField.NameOrRelativeType).CleanWhitespace().Replace("- ", "-");
            return (nameOrRelativeType.Split(new char[] { ' ', '.' }, StringSplitOptions.RemoveEmptyEntries).Count() == 3);
        }

        private bool IsRelativeInfo(Row r)
        {
            string relationshipStr = GetContents(r, DeclarationField.NameOrRelativeType).ToLower();
            return (!relationshipStr.IsNullOrWhiteSpace()
                    && (!relationshipStr.Contains("фамилия")) 
                    && (!relationshipStr.Contains("фио"))
                    && GetContents(r, DeclarationField.Occupation).IsNullOrWhiteSpace());
        }

        private PublicServant ParsePublicServantInfo(Row r)
        {
            string occ = GetContents(r, DeclarationField.Occupation);
            var res = new PublicServant()
            {
                Name = GetContents(r, DeclarationField.NameOrRelativeType),
                Occupation = occ
            };

            FillPersonProperties(r, res);

            return res;
        }

        private Relative ParseRelativeInfo(Row r)
        {
            var res = new Relative()
            {
                RelationType = ParseRelationType(GetContents(r, DeclarationField.NameOrRelativeType))
            };

            FillPersonProperties(r, res);

            return res;
        }

        private string GetContents(Row r, DeclarationField f)
        {
            return r.Cells[DeclarationProperties.ColumnOrdering[f].Value].GetText().Trim();
        }

        private void FillPersonProperties(Row r, Person p)
        {
            var ownedProperty = ParseOwnedProperty(r);
            if (ownedProperty != null) { p.RealEstateProperties.AddRange(ownedProperty); }

            var stateProperty = ParseStateProperty(r);
            if (stateProperty != null) { p.RealEstateProperties.AddRange(stateProperty); }

            string vehicle = GetContents(r, DeclarationField.Vehicle);
            if (!String.IsNullOrEmpty(vehicle) && vehicle.Trim() != "-") { p.Vehicles.Add(vehicle); }

            p.DeclaredYearlyIncome = ParseDeclaredIncome(GetContents(r, DeclarationField.DeclaredYearlyIncome));
            if (DeclarationProperties.ColumnOrdering[DeclarationField.DataSources] != null)
            {
                p.DataSources = ParseDataSources(GetContents(r, DeclarationField.DataSources));
            }
            
        }

        private static RelationType ParseRelationType(string strRel)
        {
            switch (strRel.ToLower().Replace("  ", " ").Trim().RemoveStupidTranslit().Replace("- ", "-").Replace("-\n", "-"))
            {
                case "супруг": return RelationType.MaleSpouse;
                case "супруга": return RelationType.FemaleSpouse;
                case "несовершен-нолетняя дочь": return RelationType.Child;
                case "несовершенно-летняя дочь": return RelationType.Child;
                case "несовершеннолет-няя дочь": return RelationType.Child;
                case "несовершеннолетняя дочь": return RelationType.Child;
                case "несовершенно-летний сын": return RelationType.Child;
                case "несовершеннолет-ний сын": return RelationType.Child;                                               
                case "несовершеннолетний сын": return RelationType.Child;
                case "несовершеннолетний ребенок": return RelationType.Child;
                default: throw new ArgumentOutOfRangeException(strRel, $"Неизвестный тип родственника: {strRel}");
            }
        }

        private IEnumerable<RealEstateProperty> ParseOwnedProperty(Row r)
        {
            IEnumerable<string> originalNames;
            IEnumerable<RealEstateType> propertyTypes;
            IEnumerable<OwnershipType> ownershipTypes;
            IEnumerable<string> shares;            
            string estateTypeStr = GetContents(r, DeclarationField.OwnedRealEstateType);
            if (String.IsNullOrWhiteSpace(estateTypeStr) || estateTypeStr.Trim() == "-") return null;

            // FIXME all this splitting/recombining data stuff should be replaced with simpler logic
            if (DeclarationProperties.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                originalNames = new List<string>() { estateTypeStr };
                propertyTypes = ParseRealEstateTypes(estateTypeStr);
                ownershipTypes = ParseOwnershipTypes(GetContents(r, DeclarationField.OwnedRealEstateOwnershipType));
                shares = ParseOwnershipShares(GetContents(r, DeclarationField.OwnedRealEstateOwnershipType), ownershipTypes);
            }
            else
            {
                var combinedData = ParsePropertyAndOwnershipTypes(estateTypeStr.CleanWhitespace());

                propertyTypes = combinedData.Select(info => info.Type);
                ownershipTypes = combinedData.Select(info => info.OwnershipType);
                shares = combinedData.Select(info => info.ShareText);
                originalNames = combinedData.Select(info => info.OriginalName);
            }

            string areaStr = GetContents(r, DeclarationField.OwnedRealEstateArea).CleanWhitespace();
            IEnumerable<decimal?> areas = ParseAreas(areaStr);
            
            IEnumerable<Country> countries = ParseCountries(GetContents(r, DeclarationField.OwnedRealEstateCountry));

            var res = new List<RealEstateProperty>();

            for (int i = 0; i < propertyTypes.Count(); i++)
            {
                res.Add(new RealEstateProperty(ownershipTypes.ElementAt(i), propertyTypes.ElementAt(i), countries.ElementAtOrDefault(i), areas.ElementAt(i), originalNames.ElementAt(i), shares.ElementAt(i)));
            }
            return res;
        }

        private IEnumerable<RealEstateProperty> ParseStateProperty(Row r)
        {
            IEnumerable<RealEstateType> propertyTypes;
            string propTypeStr = GetContents(r, DeclarationField.StatePropertyType);
            if (string.IsNullOrWhiteSpace(propTypeStr) || propTypeStr.Trim() == "-" || propTypeStr.Trim() == "-\n-") return null;

            if (DeclarationProperties.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                propertyTypes = ParseRealEstateTypes(propTypeStr);
            }
            else
            {
                propertyTypes = ParseStatePropertyTypesWithUsageInfo(propTypeStr.Replace("\\0", ")"));
            }


            OwnershipType ownershipType = OwnershipType.InUse; // OwnershipType.NotAnOwner;
            string share = "";
            string areaStr = GetContents(r, DeclarationField.StatePropertyArea).Trim();
            IEnumerable<decimal?> areas = ParseAreas(areaStr);


            IEnumerable<Country> countries = ParseCountries(GetContents(r, DeclarationField.StatePropertyCountry));

            var res = new List<RealEstateProperty>();
            for (int i = 0; i < propertyTypes.Count(); i++)
            {
                res.Add(new RealEstateProperty(ownershipType, propertyTypes.ElementAt(i), countries.ElementAt(i), areas.ElementAt(i), propTypeStr, share));
            }

            return res;
        }

        private IEnumerable<RealEstateType> ParseRealEstateTypes(string strTypes)
        {
            return new List<RealEstateType>() { ParseRealEstateType(strTypes) };
        }

        private RealEstateType ParseRealEstateType(string strType)
        {
            string key = strType.ToLower().RemoveStupidTranslit()
                                          .Trim('\"')
                                          .Replace('\n', ' ')
                                          .Replace(';', ' ')
                                          .Replace("   ", " ")
                                          .Replace("  ", " ")
                                          .Trim();

            if (PropertyTypes.ContainsKey(key))
            {
                return PropertyTypes[key];
            }
            else
            {
                throw new ArgumentOutOfRangeException("strType", $"Неизвестный тип недвижимости: {strType}");
            }
        }

        private static IEnumerable<OwnershipType> ParseOwnershipTypes(string strOwn)
        {
            return new List<OwnershipType>() { ParseOwnershipType(strOwn) };
        }

        private static OwnershipType ParseOwnershipType(string strOwn)
        {
            string str = strOwn.ToLower().Trim();
            OwnershipType res;
            if (str.StartsWith("индивидуальная")) res = OwnershipType.Individual;
            else if (str.StartsWith("собственность")) res = OwnershipType.Individual;
            else if (str.StartsWith("общая совместная")) res = OwnershipType.Joint;
            else if (str.StartsWith("совместная")) res = OwnershipType.Joint;

            else if (str.StartsWith("делевая")) res = OwnershipType.Shared;
            else if (str.StartsWith("долевая")) res = OwnershipType.Shared;
            else if (str.StartsWith("долеявая")) res = OwnershipType.Shared;
            else if (str.StartsWith("общая долевая")) res = OwnershipType.Shared;
            else if (str.StartsWith("общая, долевая")) res = OwnershipType.Shared;
            else if (str.StartsWith("общедолевая")) res = OwnershipType.Shared;

            else if (str.StartsWith("общая")) res = OwnershipType.Joint;

            else if (String.IsNullOrWhiteSpace(str) || str == "-") res = OwnershipType.NotAnOwner;
            else throw new ArgumentOutOfRangeException("strOwn", $"Неизвестный тип собственности: {strOwn}");

            return res;
        }

        private class RealEstateInfo
        {
            public string OriginalName { get; set; }
            public RealEstateType Type { get; set; }
            public OwnershipType OwnershipType { get; set; }
            public string ShareText { get; set; }
        }

        private IEnumerable<RealEstateInfo> ParsePropertyAndOwnershipTypes(string strPropInfo)
        {
            var res = new List<RealEstateInfo>();

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
                    OwnershipType ownershipType = ParseOwnershipType(strOwnType);
                    string share = ParseOwnershipShare(strOwnType, ownershipType);
                    res.Add(new RealEstateInfo()
                    {
                        OriginalName = strPropType,
                        Type = realEstateType,
                        OwnershipType = ownershipType,
                        ShareText = share
                    });

                    startingPos = rightParenPos + 1;
                }

                leftParenPos = strPropInfo.IndexOf('(', rightParenPos);
            }

            return res;
        }

        private IEnumerable<RealEstateType> ParseStatePropertyTypesWithUsageInfo(string strPropInfo)
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
                // FIXME else what?

                leftParenPos = strPropInfo.IndexOf('(', rightParenPos + 1);
            }

            return res;
        }

        private static bool ContainsOwnershipType(string str)
        {
            string strProc = str.Trim().ToLower();
            return (strProc.Contains("индивидуальная") || strProc.Contains("долевая") || strProc.Contains("общая") || strProc.Contains("аренда") ||
                    strProc.Contains("пользование") || strProc.Contains("предоставление") || strProc.Contains("найм"));
        }

        private static IEnumerable<string> ParseOwnershipShares(string strOwn, IEnumerable<OwnershipType> ownTypes)
        {
            var res = new List<string>();
            foreach (var ownType in ownTypes)
            {
                // FIXME на самом деле тут ещё нужно строковый параметр на отдельные подстроки разбивать
                res.Add(ParseOwnershipShare(strOwn, ownType));
            }

            return res;
        }

        private static string ParseOwnershipShare(string strOwn, OwnershipType ownType)
        {
            string res = strOwn;
            if (ownType == OwnershipType.Shared)
            {
                String[] strToRemove = new String[] { "Общедолевая", "Общая долевая", "Общая, долевая", "Делевая", "Долевая", "Долеявая",
                                                      "Общая, долевая", "Доля", "Доли", "Долей", "Размер", " ", "(", ")" };
                foreach (string str in strToRemove)
                {
                    res = res.Replace(str, "");
                    res = res.Replace(str.ToLower(), "");
                }

                res = res.Trim(',');

                return res;
            }
            else
            { 
                return "";
            }
        }

        private static readonly string[] AreaSeparators = new string[] { "\n", " " };
        private static IEnumerable<decimal?> ParseAreas(string strAreas)
        {
            var res = new List<decimal?>();
            foreach (var str in strAreas.Split(AreaSeparators, StringSplitOptions.RemoveEmptyEntries))
            {
                decimal? area;
                if (String.IsNullOrWhiteSpace(str) || str == "-")
                {
                    area = null;
                }
                else
                {
                    area = str.ParseDecimalValue();
                }

                res.Add(area);
            }

            return res;
        }

        private static readonly string[] CountrySeparators = new string[] { "\n" };
        private static IEnumerable<Country> ParseCountries(string strCountries)
        {
            var res = new List<Country>();
            var parts = strCountries.Split(CountrySeparators, StringSplitOptions.RemoveEmptyEntries);

            foreach (var part in parts)
            {
                res.Add(ParseCountry(part));
            }

            return res;
        }

        private static Country ParseCountry(string strCountry)
        {
            if (String.IsNullOrWhiteSpace(strCountry) || strCountry.Trim() == "-")
            {
                return Country.Undefined;
            }
            switch (strCountry.Trim().ToLower())
            {
                case "беларусь": return Country.Belarus;
                case "бельгия": return Country.Belgium;
                case "республика беларусь": return Country.Belarus;
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
                default: throw new ArgumentOutOfRangeException();
            }
        }

        private static decimal? ParseDeclaredIncome(string strIncome)
        {
            if (String.IsNullOrWhiteSpace(strIncome) || strIncome.Trim() == "-" || strIncome.Trim() == "–"
                || strIncome.Contains("нет")) return null;
            else
            {
                int leftParenPos = strIncome.IndexOf("(");
                if (leftParenPos == -1)
                {
                    return strIncome.ParseDecimalValue();
                }
                else
                {
                    return strIncome.Substring(0, leftParenPos).ParseDecimalValue();
                }
                
            }
                
        }

        private static string ParseDataSources(string src)
        {
            if (src.Trim() == "-") return null;
            else return src;
        }
    }
}
