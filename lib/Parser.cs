using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Threading;
using System.Collections.Generic;
using System.Linq;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    
    public class Parser : RealtyParser
    { 
        DateTime FirstPassStartTime;
        DateTime SecondPassStartTime;
        bool FailOnRelativeOrphan;
        public int NameOrRelativeTypeColumn { set; get; } = 1;

        public Parser(IAdapter adapter, bool failOnRelativeOrphan = true)
        {
            Adapter = adapter;
            FailOnRelativeOrphan = failOnRelativeOrphan;
            ParserNumberFormatInfo.NumberDecimalSeparator = ",";
            
        }
        public static void InitializeSmartParser()
        {
            Smart.Parser.Adapters.AsposeLicense.SetAsposeLicenseFromEnvironment();

            var culture = new System.Globalization.CultureInfo("ru-RU");
            Thread.CurrentThread.CurrentCulture = culture;
            var envVars = Environment.GetEnvironmentVariables();
            if (envVars.Contains("DECLARATOR_CONV_URL"))
            {
                IAdapter.ConvertedFileStorageUrl = envVars["DECLARATOR_CONV_URL"].ToString();
            }
        }

        public Declaration InitializeDeclaration(ColumnOrdering columnOrdering, int? user_documentfile_id)
        {
            // parse filename
            int? documentfile_id;
            string archive;
            bool result = DataHelper.ParseDocumentFileName(Adapter.DocumentFile, out documentfile_id, out archive);
            if (user_documentfile_id.HasValue)
                documentfile_id = user_documentfile_id;

            DeclarationProperties properties = new DeclarationProperties()
            {
                SheetTitle = columnOrdering.Title,
                Year = columnOrdering.Year,
                DocumentFileId = documentfile_id,
                ArchiveFileName = archive,
                SheetNumber = Adapter.GetWorksheetIndex(),
                DocumentUrl = Adapter.GetDocumentUrlFromMetaTag()
            };
            if (columnOrdering.YearFromIncome != null)
            {
                if (properties.Year != null)
                {
                    properties.Year = Math.Max(columnOrdering.YearFromIncome.Value, properties.Year.Value);
                }
                else
                {
                    properties.Year = columnOrdering.YearFromIncome;
                }
            }
            Declaration declaration = new Declaration()
            {
                Properties = properties
            };
            return declaration;
        }


        bool IsHeaderRow(DataRow row, out ColumnOrdering columnOrdering)
        {
            columnOrdering = null;
            if (!ColumnDetector.WeakHeaderCheck(Adapter, row.Cells)) 
                return false;
            try
            {
                columnOrdering = new ColumnOrdering();
                ColumnDetector.ReadHeader(Adapter, row.GetRowIndex(), columnOrdering);
                return true;
            }
            catch (Exception e)
            {
                Logger.Debug(String.Format("Cannot parse possible header, row={0}, error={1}, so skip it may be it is a data row ", e.ToString(), row.GetRowIndex()));
            }
            return false;
        }

        public Declaration Parse(ColumnOrdering columnOrdering, bool updateTrigrams, int? documentfile_id)
        {
            FirstPassStartTime = DateTime.Now;

            Declaration declaration =  InitializeDeclaration(columnOrdering, documentfile_id);

            int rowOffset = columnOrdering.FirstDataRow;

            TBorderFinder borderFinder = new TBorderFinder(declaration, FailOnRelativeOrphan);
            
            if (columnOrdering.Section != null)
            {
                borderFinder.CreateNewSection(rowOffset, columnOrdering.Section);
            }

            bool skipEmptyPerson = false;
            string prevPersonName = "";

            for (int row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                DataRow currRow = Adapter.GetRow(columnOrdering, row);
                if (currRow == null || currRow.IsEmpty())
                {
                    continue;
                }
                if (IAdapter.IsNumbersRow(currRow.Cells))
                {
                    continue;
                }
                Logger.Debug(String.Format("currRow {1}: {0}", currRow.DebugString(), row));

                string sectionName;
                if (IAdapter.IsSectionRow(currRow.Cells, columnOrdering.GetMaxColumnEndIndex(), false, out sectionName))
                {
                    borderFinder.CreateNewSection(row, sectionName);
                    continue;
                }
                {
                    ColumnOrdering newColumnOrdering;
                    if (IsHeaderRow(currRow, out newColumnOrdering))
                    {
                        columnOrdering = newColumnOrdering;
                        row = newColumnOrdering.GetPossibleHeaderEnd() - 1; // row++ in "for" cycle
                        continue;
                    }
                }

                if (updateTrigrams) ColumnPredictor.UpdateByRow(columnOrdering, currRow);

                if (!currRow.InitPersonData(prevPersonName))
                {
                    // be robust, ignore errors see 8562.pdf.docx in tests
                    continue;
                }

                if (currRow.PersonName != String.Empty)
                {
                    prevPersonName = currRow.PersonName; 
                    borderFinder.CreateNewDeclarant(Adapter, currRow);
                    if (borderFinder.CurrentPerson != null)
                        skipEmptyPerson = false;
                }
                else if  (currRow.RelativeType != String.Empty)
                {
                    if (!skipEmptyPerson)
                    {
                        try
                        {
                            borderFinder.CreateNewRelative(currRow);
                        }
                        catch (SmartParserRelativeWithoutPersonException e)
                        {
                            skipEmptyPerson = true;
                            Logger.Error(e.Message);
                            continue;
                        }
                    }
                }
                else 
                {
                    if (borderFinder.CurrentPerson == null && FailOnRelativeOrphan)
                    {
                        skipEmptyPerson = true;
                        Logger.Error(String.Format("No person to attach info on row={0}", row));
                        continue;
                    }
                }
                if (!skipEmptyPerson)
                {
                    borderFinder.AddInputRowToCurrentPerson(columnOrdering, currRow);
                    if (declaration.Properties.Year == null && columnOrdering.ContainsField(DeclarationField.IncomeYear))
                    {
                        var incomeYear = currRow.GetDeclarationField(DeclarationField.IncomeYear);
                        if (incomeYear != null) {
                            declaration.Properties.Year = int.Parse(incomeYear.Text);
                        }
                    }
                }

            }
            if (updateTrigrams) ColumnPredictor.WriteData();

            Logger.Info("Parsed {0} declarants", declaration.PublicServants.Count());
            if (!ColumnOrdering.SearchForFioColumnOnly)
                ParsePersonalProperties(declaration);

            return declaration;
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

        public Declaration ParsePersonalProperties(Declaration declaration)
        {
            ForgetThousandMultiplier(declaration);
            SecondPassStartTime = DateTime.Now;
            int count = 0;
            int total_count = declaration.PublicServants.Count();
            Decimal totalIncome = 0;
            int max_relatives_count = 15;

            foreach (PublicServant servant in declaration.PublicServants)
            {
                if (servant.Relatives.Count() > max_relatives_count)
                {
                    throw new SmartParserException(String.Format("too many relatives (>{0})", max_relatives_count));
                }
            
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
                            if (ParseIncome(currRow, person, declaration.Properties.IgnoreThousandMultipler))
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
                    for (int i = 0; i < splitVehicleModels.Length; ++i )
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


        public IAdapter Adapter { get; set; }
    }
}
