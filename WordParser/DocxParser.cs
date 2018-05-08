﻿using System;
using System.Collections.Generic;
using System.Linq;

using TI.Declarator.ParserCommon;
using Xceed.Words.NET;

namespace TI.Declarator.WordParser
{
    public class DocXParser : IDeclarationParser
    {
        private ColumnOrdering ColumnOrder;
        private Dictionary<string, RealEstateType> PropertyTypes;

        public DocXParser(Dictionary<string, RealEstateType> propertyTypes)
        {
            this.PropertyTypes = propertyTypes;
        }


        public IEnumerable<PublicServant> Parse(string filepath)
        {
            DocX doc = DocX.Load(filepath);
            var leadTable = doc.Tables.First();

            // FIXME удалить трейсы
            int ind = 0;
            foreach(var cell in leadTable.Rows.First().Cells)
            {
                Console.WriteLine($"{ind} {cell.Paragraphs.First().Text} {cell.GridSpan}");
                ind++;
            }

            ind = 0;
            foreach (var cell in leadTable.Rows.Skip(1).First().Cells)
            {
                Console.WriteLine($"{ind} {cell.Paragraphs.First().Text} {cell.GridSpan}");
                ind++;
            }

            ColumnOrder = ExamineHeader(leadTable);

            return Parse(doc);
        }

        private ColumnOrdering ExamineHeader(Table t)
        {
            Row header = t.Rows.First();

            ColumnOrdering res = new ColumnOrdering();
            int colCount = 0;
            int index = 0;
            foreach (var cell in header.Cells)
            {
                string text = cell.Paragraphs.First().Text;

                Field field;
                if (cell.GridSpan <= 1)
                {
                    if (!text.IsNullOrWhiteSpace())
                    {
                        field = HeaderHelpers.GetField(text);
                        res.Add(field, index);
                        index++;
                        colCount++;
                    }
                }
                // current cell spans several columns, so the header probably occupies two rows instead of just one
                // with the second row reserved for subheaders
                else
                {
                    int span = cell.GridSpan == 0 ? 1 : cell.GridSpan;
                    Row auxRow = t.Rows.Skip(1).First();
                    var auxCellsIter = auxRow.Cells.GetEnumerator();
                    auxCellsIter.MoveNext();
                    int auxColCount = 0;
                    
                    while (auxColCount < colCount + span)
                    {
                        var auxCell = auxCellsIter.Current;
                        if (auxColCount >= colCount)
                        {
                            string fullText = text + " " + auxCell.Paragraphs.First().Text;
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

        private IEnumerable<PublicServant> Parse(DocX doc, int rowOffset = 1)
        {
            var leadTable = doc.Tables.First();
            var res = new List<PublicServant>();
            PublicServant currentServant = null;
            Person currentPerson = null;
            foreach (Row r in leadTable.Rows.Skip(rowOffset))
            {
                if (IsPublicServantInfo(r))
                {
                    PublicServant pServ = ParsePublicServantInfo(r);
                    currentServant = pServ;
                    currentPerson = pServ;

                    res.Add(pServ);
                }
                else if (IsRelativeInfo(r))
                {
                    Relative pRel = ParseRelativeInfo(r);
                    currentServant.Relatives.Add(pRel);
                    currentPerson = pRel;
                }                
            }

            return res;
        }

        private bool IsPublicServantInfo(Row r)
        {
            string nameOrRelativeType = GetContents(r, Field.NameOrRelativeType);
            return (nameOrRelativeType.Split(new char[] { ' ' }, StringSplitOptions.RemoveEmptyEntries).Count() == 3);
        }

        private bool IsRelativeInfo(Row r)
        {
            return (!GetContents(r, Field.NameOrRelativeType).IsNullOrWhiteSpace()
                    && GetContents(r, Field.Occupation).IsNullOrWhiteSpace());
        }

        private PublicServant ParsePublicServantInfo(Row r)
        {
            string occ = GetContents(r, Field.Occupation);
            var res = new PublicServant()
            {
                Name = GetContents(r, Field.NameOrRelativeType),
                Occupation = occ
            };

            FillPersonProperties(r, res);

            return res;
        }

        private Relative ParseRelativeInfo(Row r)
        {
            var res = new Relative()
            {
                RelationType = ParseRelationType(GetContents(r, Field.NameOrRelativeType))
            };

            FillPersonProperties(r, res);

            return res;
        }

        private string GetContents(Row r, Field f)
        {
            return r.Cells[ColumnOrder[f]].GetText().Trim();
        }

        private void FillPersonProperties(Row r, Person p)
        {
            var ownedProperty = ParseOwnedProperty(r);
            if (ownedProperty != null) { p.RealEstateProperties.Add(ownedProperty); }

            var stateProperty = ParseStateProperty(r);
            if (stateProperty != null) { p.RealEstateProperties.Add(stateProperty); }

            string vehicle = GetContents(r, Field.Vehicle);
            if (!String.IsNullOrEmpty(vehicle) && vehicle.Trim() != "-") { p.Vehicles.Add(vehicle); }

            p.DeclaredYearlyIncome = ParseDeclaredIncome(GetContents(r, Field.DeclaredYearlyIncome));
            p.DataSources = ParseDataSources(GetContents(r, Field.DataSources));
        }

        private static RelationType ParseRelationType(string strRel)
        {
            switch (strRel.ToLower().Trim().RemoveStupidTranslit())
            {
                case "супруг": return RelationType.MaleSpouse;
                case "супруга": return RelationType.FemaleSpouse;
                case "несовершеннолетний ребенок": return RelationType.Child;
                default: throw new ArgumentOutOfRangeException(strRel, $"Неизвестный тип родственника: {strRel}");
            }
        }

        private RealEstateProperty ParseOwnedProperty(Row r)
        {
            string estateType = GetContents(r, Field.OwnedRealEstateType);
            if (String.IsNullOrWhiteSpace(estateType) || estateType.Trim() == "-") return null;

            RealEstateType propertyType = ParseRealEstateType(estateType);
            OwnershipType ownershipType = ParseOwnershipType(GetContents(r, Field.RealEstateOwnershipType));
            string share = ParseOwnershipShare(GetContents(r, Field.RealEstateOwnershipType), ownershipType);
            decimal? area;
            string areaStr = GetContents(r, Field.OwnedRealEstateArea).Trim();
            if (String.IsNullOrWhiteSpace(areaStr) || areaStr == "-")
            {
                area = null;
            }
            else
            {
                area = GetContents(r, Field.OwnedRealEstateArea).ParseDecimalValue();
            }
            Country country = ParseCountry(GetContents(r, Field.OwnedRealEstateCountry));
            return new RealEstateProperty(ownershipType, propertyType, country, area, estateType, share);
        }

        private RealEstateProperty ParseStateProperty(Row r)
        {
            string propType = GetContents(r, Field.StatePropertyType);
            if (string.IsNullOrWhiteSpace(propType) || propType.Trim() == "-") return null;

            RealEstateType propertyType = ParseRealEstateType(propType);
            OwnershipType ownershipType = OwnershipType.NotAnOwner;
            string share = "";
            decimal? area;
            string areaStr = GetContents(r, Field.StatePropertyArea).Trim();
            if (String.IsNullOrWhiteSpace(areaStr) || areaStr == "-")
            {
                area = null;
            }
            else
            {
                area = areaStr.ParseDecimalValue();
            }
            Country country = ParseCountry(GetContents(r, Field.StatePropertyCountry));
            return new RealEstateProperty(ownershipType, propertyType, country, area, propType, share);
        }

        private RealEstateType ParseRealEstateType(string strType)
        {
            string key = strType.ToLower().Trim('\"').Trim();
            if (PropertyTypes.ContainsKey(key))
            {
                return PropertyTypes[key];
            }
            else
            {
                throw new ArgumentOutOfRangeException("strType", $"Неизвестный тип недвижимости: {strType}");
            }
        }

        private static OwnershipType ParseOwnershipType(string strOwn)
        {
            string str = strOwn.ToLower().Trim();
            if (str.StartsWith("индивидуальная")) return OwnershipType.Individual;
            if (str.StartsWith("собственность")) return OwnershipType.Individual;
            if (str.StartsWith("общая совместная")) return OwnershipType.Coop;
            if (str.StartsWith("совместная")) return OwnershipType.Coop;

            if (str.StartsWith("делевая")) return OwnershipType.Shared;
            if (str.StartsWith("долевая")) return OwnershipType.Shared;
            if (str.StartsWith("долеявая")) return OwnershipType.Shared;
            if (str.StartsWith("общая долевая")) return OwnershipType.Shared;
            if (str.StartsWith("общая, долевая")) return OwnershipType.Shared;
            if (str.StartsWith("общедолевая")) return OwnershipType.Shared;

            if (str.StartsWith("общая")) return OwnershipType.Coop;

            if (String.IsNullOrWhiteSpace(str) || str == "-") return OwnershipType.NotAnOwner;

            throw new ArgumentOutOfRangeException("strOwn", $"Неизвестный тип собственности: {strOwn}");
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
                return "";
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
                case "республика беларусь": return Country.Belarus;
                case "венгрия": return Country.Hungary;
                case "грузия": return Country.Georgia;
                case "казахстан": return Country.Kazakhstan;
                case "российская федерация": return Country.Russia;
                case "россия": return Country.Russia;
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
            if (String.IsNullOrWhiteSpace(strIncome) || strIncome.Trim() == "-") return null;
            else return strIncome.ParseDecimalValue();
        }

        private static string ParseDataSources(string src)
        {
            if (src.Trim() == "-") return null;
            else return src;
        }
    }
}
