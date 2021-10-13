using System;
using System.Collections.Generic;
using Parser.Lib;
using TI.Declarator.ParserCommon;
using Smart.Parser.Adapters;
using System.Linq;

namespace Smart.Parser.Lib
{
    class TSecondPassParser : RealtyParser
    {
        IAdapter Adapter = null;
        Decimal TotalIncome = 0;
        const int MaxRelativesCount = 15;

        public TSecondPassParser(IAdapter adapter)
        {
            Adapter = adapter;
        }
        public void ForgetThousandMultiplier(Declaration declaration)
        {
            // the incomes are so high, that we should not multiply incomes by 1000 although the 
            // column title specify this multiplier
            List<Decimal> incomes = new List<Decimal>();

            foreach (PublicServant servant in declaration.PublicServants)
            {
                foreach (DataRow row in servant.DateRows)
                {
                    if (row.ColumnOrdering.ContainsField(DeclarationField.DeclaredYearlyIncomeThousands))
                    {
                        PublicServant dummy = new PublicServant();
                        if (ParseIncome(row, dummy, true))
                        {
                            if (dummy.DeclaredYearlyIncome != null)
                            {
                                incomes.Add(dummy.DeclaredYearlyIncome.Value);
                            }
                        }
                    }
                }
            }
            if (incomes.Count > 3)
            {
                incomes.Sort();
                Decimal medianIncome = incomes[incomes.Count / 2];
                if (medianIncome > 10000)
                {
                    declaration.Properties.IgnoreThousandMultipler = true;
                }
            }
        }

        bool ParseIncomeOneField(DataRow currRow, Person person, DeclarationField field, bool ignoreThousandMultiplier)
        {
            if (!currRow.ColumnOrdering.ContainsField(field)) return false;
            string fieldStr = currRow.GetContents(field);
            if (DataHelper.IsEmptyValue(fieldStr))
                return false;

            bool fieldInThousands = (field & DeclarationField.DeclaredYearlyIncomeThousandsMask) == DeclarationField.DeclaredYearlyIncomeThousandsMask;
            person.DeclaredYearlyIncome = DataHelper.ParseDeclaredIncome(fieldStr, fieldInThousands);
            if (!ignoreThousandMultiplier || fieldStr.Contains("тыс."))
            {
                person.DeclaredYearlyIncome *= 1000;
            }

            if (!DataHelper.IsEmptyValue(fieldStr))
                person.DeclaredYearlyIncomeRaw = NormalizeRawDecimalForTest(fieldStr);
            return true;
        }
        bool ParseIncome(DataRow currRow, Person person, bool ignoreThousandMultiplier)
        {
            try
            {
                if (ParseIncomeOneField(currRow, person, DeclarationField.DeclaredYearlyIncomeThousands, ignoreThousandMultiplier))
                {
                    return true;
                }
                else if (ParseIncomeOneField(currRow, person, DeclarationField.DeclaredYearlyIncome, true))
                {
                    return true;
                }
                else if (ParseIncomeOneField(currRow, person, DeclarationField.DeclarantIncomeInThousands, ignoreThousandMultiplier))
                {
                    return true;
                }
                else if (ParseIncomeOneField(currRow, person, DeclarationField.DeclarantIncome, true))
                {
                    return true;
                }
                return false;
            }
            catch (SmartParserFieldNotFoundException e)
            {
                if (person is Relative && (person as Relative).RelationType == RelationType.Child)
                {
                    Logger.Info("Child's income is unparsable, set it to 0 ");
                    return true;
                }
                else
                {
                    Logger.Info("Cannot find or parse income cell, keep going... ");
                    return true;
                }
            }
        }

        private void AddVehicle(DataRow r, Person person)
        {
            if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.Vehicle))
            {
                var s = r.GetContents(DeclarationField.Vehicle).Replace("не имеет", "");
                if (!DataHelper.IsEmptyValue(s))
                    person.Vehicles.Add(new Vehicle(s));
            }
            else if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.DeclarantVehicle))
            {
                var s = r.GetContents(DeclarationField.DeclarantVehicle).Replace("не имеет", "");
                if (!DataHelper.IsEmptyValue(s))
                    person.Vehicles.Add(new Vehicle(s));
            }
            else if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.VehicleType))
            {

                var t = r.GetContents(DeclarationField.VehicleType).Replace("не имеет", "");
                var m = r.GetContents(DeclarationField.VehicleModel, false).Replace("не имеет", "");
                var splitVehicleModels = TextHelpers.SplitByEmptyLines(m);
                if (splitVehicleModels.Length > 1)
                {
                    for (int i = 0; i < splitVehicleModels.Length; ++i)
                    {
                        person.Vehicles.Add(new Vehicle(splitVehicleModels[i], "", splitVehicleModels[i]));
                    }
                }
                else
                {
                    var text = t + " " + m;
                    if (t == m)
                    {
                        text = t;
                        m = "";
                    }
                    if (!DataHelper.IsEmptyValue(m) || !DataHelper.IsEmptyValue(t))
                        person.Vehicles.Add(new Vehicle(text.Trim(), t, m));
                }
            }

        }

        private void ParseOneDeclarantAndHisRelatives(bool ignoreThousandMultipler, PublicServant servant)
        {
            List<Person> declarantAndRelatives = new List<Person>() { servant };
            declarantAndRelatives.AddRange(servant.Relatives);

            foreach (Person person in declarantAndRelatives)
            {
                if (person is PublicServant)
                {
                    Logger.Debug("PublicServant: " + ((PublicServant)person).NameRaw.ReplaceEolnWithSpace());
                }
                bool foundIncomeInfo = false;

                List<DataRow> rows = new List<DataRow>();
                foreach (DataRow row in person.DateRows)
                {
                    if (row == null || row.Cells.Count == 0)
                    {
                        continue;
                    }

                    if (Adapter.IsExcel() &&
                        !row.IsEmpty(DeclarationField.StatePropertyType,
                            DeclarationField.MixedRealEstateType,
                            DeclarationField.OwnedRealEstateType) &&
                        row.IsEmpty(DeclarationField.MixedRealEstateSquare,
                            DeclarationField.OwnedRealEstateSquare,
                            DeclarationField.StatePropertySquare,
                            DeclarationField.OwnedRealEstateCountry,
                            DeclarationField.MixedRealEstateCountry,
                            DeclarationField.StatePropertyCountry,
                            DeclarationField.NameOrRelativeType) &&
                        rows.Count > 0)
                    {
                        Logger.Debug("Merge row to the last if state and square cell is empty");
                        rows.Last().Merge(row);
                    }
                    else
                    {
                        rows.Add(row);
                    }
                }


                foreach (var currRow in rows)
                {
                    if (!foundIncomeInfo)
                    {
                        if (ParseIncome(currRow, person, ignoreThousandMultipler))
                        {
                            TotalIncome += person.DeclaredYearlyIncome == null ? 0 : person.DeclaredYearlyIncome.Value;
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

        public int ParseDeclarants(Declaration declaration)
        {
            ForgetThousandMultiplier(declaration);
            var secondPassStartTime = DateTime.Now;
            int allDeclarantsCount = declaration.PublicServants.Count();

            int  goodDeclarantCount = 0;
            var exceptions = new List<Exception>();

            foreach (PublicServant declarant in declaration.PublicServants)
            {
                if (declarant.Relatives.Count() > MaxRelativesCount)
                {
                    throw new SmartParserException(String.Format("too many relatives (>{0})", MaxRelativesCount));
                }
                try
                {
                    ParseOneDeclarantAndHisRelatives(declaration.Properties.IgnoreThousandMultipler, declarant);
                    goodDeclarantCount++;
                    if (goodDeclarantCount % 1000 == 0)
                    {
                        double time_sec = DateTime.Now.Subtract(secondPassStartTime).TotalSeconds;
                        Logger.Info("Done: {0:0.00}%", 100.0 * goodDeclarantCount / allDeclarantsCount);
                        Logger.Info("Rate: {0:0.00} declarant in second", goodDeclarantCount / time_sec);
                    }
                }
                catch (SmartParserExceptionBase e)
                {
                    if (goodDeclarantCount < 10)
                    {
                        throw e;
                    }
                    if (exceptions.Count > 10)
                    {
                        throw exceptions[0];
                    }
                    Logger.Error(String.Format("ignore exception {0}, since there are {1} good declarant count",
                        e.Message, goodDeclarantCount));
                    exceptions.Add(e);
                }

            }
            Logger.Info("Total income: {0}", TotalIncome);
            return goodDeclarantCount;
        }
    }
}
