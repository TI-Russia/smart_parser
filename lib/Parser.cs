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
                properties.Year = columnOrdering.YearFromIncome;
            }
            /*if (properties.Year == null)
            {
                properties.Year = columnOrdering.YearFromIncome;
            }*/
            Declaration declaration = new Declaration()
            {
                Properties = properties
            };
            return declaration;
        }


        class TBorderFinder
        {
            DeclarationSection CurrentSection = null;
            PublicServant CurrentDeclarant = null;
            public TI.Declarator.ParserCommon.Person CurrentPerson = null;
            Declaration _Declaration;
            bool FailOnRelativeOrphan;

            public TBorderFinder(Declaration declaration, bool failOnRelativeOrphan)
            {
                _Declaration = declaration;
                FailOnRelativeOrphan = failOnRelativeOrphan;
            }
            public void FinishDeclarant()
            {
                CurrentDeclarant = null;
                CurrentPerson = null;
            }
            public void CreateNewSection(int row, string sectionTitle)
            {
                CurrentSection = new DeclarationSection() { Row = row, Name = sectionTitle };
                Logger.Debug(String.Format("find section at line {0}:'{1}'", row, sectionTitle));
                FinishDeclarant();
            }

            //  see 8562.pdf.docx  in tests
            //  calc string width using graphics.MeasureString methods
            bool DivideDeclarantAndRelativesBySoftEolns(ColumnOrdering columnOrdering, DataRow row)
            {
                if (CurrentDeclarant.Relatives.Count() > 0)
                {
                    return false;
                }
                if (!columnOrdering.ContainsField(DeclarationField.NameOrRelativeType)) return false;
                Cell nameCell = row.GetDeclarationField(DeclarationField.NameOrRelativeType);
                if (!(nameCell is OpenXmlWordCell) && !(nameCell is HtmlAdapterCell)) return false;
                if (nameCell is null) return false;
                if (nameCell.IsEmpty) return false;
                if (row.adapter.IsExcel()) return false; // no font info
                List<string> lines = nameCell.GetLinesWithSoftBreaks();
                if (lines.Count < 2) return false;
                List<int> borders  = new List<int>() { 0 };

                for (int i = 1;  i< lines.Count; ++i)
                {
                    if (DataHelper.ParseRelationType(lines[i], false) != RelationType.Error)
                    {
                        borders.Add(i);
                    }
                }
                if (borders.Count == 1) return false;
                List<DataRow> dividedLines = new List<DataRow>();
                for (int i = 0; i < borders.Count; ++i)
                {
                    dividedLines.Add(row.DeepClone());
                }
                for (int i = 0; i < row.Cells.Count; ++i)
                {
                    var divided = row.Cells[i].GetLinesWithSoftBreaks();
                    int start = 0;
                    for (int k = 0; k < borders.Count; ++k)
                    {
                        int end = (k + 1 == borders.Count) ? divided.Count : borders[k + 1];
                        if (start < divided.Count)
                        {
                            string value = String.Join("\n", divided.Skip(start).Take(end - start));
                            if (value.Length > 0)
                            {
                                dividedLines[k].Cells[i].Text = value;
                                dividedLines[k].Cells[i].IsEmpty = false;
                            }
                        }
                        start = end;
                    }
                }
                for (int k = 0; k < borders.Count; ++k)
                {
                    DataRow currRow = dividedLines[k];
                    var nameOrRelativeType = currRow.GetDeclarationField(DeclarationField.NameOrRelativeType).Text.Replace("не имеет", "");
                    if (k == 0)
                    {
                        currRow.PersonName = nameOrRelativeType;
                        currRow.Occupation = row.Occupation.Replace("не имеет", "");
                        currRow.Department = row.Department;
                        if (currRow.Department != null)
                            currRow.Department = currRow.Department.Replace("не имеет", "");
                        InitDeclarantProperties(currRow);
                    }
                    else
                    {
                        if (!DataHelper.IsRelativeInfo(nameOrRelativeType))
                        {
                            Logger.Error(String.Format("cannot parse relative {0}", nameOrRelativeType.ReplaceEolnWithSpace()));
                            return false;
                        }
                        else
                        {
                            currRow.SetRelative(nameOrRelativeType);
                        }

                        CreateNewRelative(currRow);
                    }
                    CurrentPerson.DateRows.Add(dividedLines[k]);
                }
                return true;
            }
            public void AddInputRowToCurrentPerson(ColumnOrdering columnOrdering,  DataRow row)
            {
                if (CurrentPerson != null)
                {
                    if (!DivideDeclarantAndRelativesBySoftEolns(columnOrdering, row))
                    {
                        CurrentPerson.DateRows.Add(row);
                        TransposeTableByRelatives(columnOrdering, row);
                    }
                }
            }

            void CopyRelativeFieldToMainCell(DataRow row, DeclarationField relativeMask,  DeclarationField f, ref DataRow childRow)
            {
                if ((f & relativeMask) > 0)
                {
                    var value = row.GetContents(f, false);
                    if (!DataHelper.IsEmptyValue(value))
                    {
                        if (childRow == null)
                        {
                            childRow = row.DeepClone();
                        }
                        f = (f & ~relativeMask) | DeclarationField.MainDeclarant;
                        var declarantCell = childRow.GetDeclarationField(f);
                        declarantCell.Text = value;
                        declarantCell.IsEmpty = false;
                    }
                }

            }
            public void TransposeTableByRelatives(ColumnOrdering columnOrdering, DataRow row)
            {
                DataRow childRow = null;
                DataRow spouseRow = null;
                foreach (var f in columnOrdering.ColumnOrder.Keys)
                {
                    CopyRelativeFieldToMainCell(row, DeclarationField.DeclarantChild, f, ref childRow);
                    CopyRelativeFieldToMainCell(row, DeclarationField.DeclarantSpouse, f, ref spouseRow);
                }
                if (childRow != null)
                {
                    childRow.RelativeType = "несовершеннолетний ребенок";
                    CreateNewRelative(childRow);
                    CurrentPerson.DateRows.Add(childRow);
                    Logger.Debug("Create artificial line for a child");
                }
                if (spouseRow != null)
                {
                    spouseRow.RelativeType = "супруга";
                    CreateNewRelative(spouseRow);
                    CurrentPerson.DateRows.Add(spouseRow);
                    Logger.Debug("Create artificial line for a spouse");
                }
            }

            public void InitDeclarantProperties(DataRow row)
            {
                CurrentDeclarant.NameRaw = row.PersonName.RemoveStupidTranslit().Replace("не имеет", "");
                CurrentDeclarant.Occupation = row.Occupation.Replace("не имеет", "").NormSpaces();
                CurrentDeclarant.Department = row.Department.NormSpaces();
                CurrentDeclarant.Ordering = row.ColumnOrdering;
            }

            public void CreateNewDeclarant(IAdapter adapter, DataRow row)
            {
                Logger.Debug("Declarant {0} at row {1}", row.PersonName, row.GetRowIndex());
                CurrentDeclarant = new PublicServant();
                InitDeclarantProperties(row);
                if (CurrentSection != null)
                {
                    CurrentDeclarant.Department = CurrentSection.Name;
                }
                
                CurrentDeclarant.Index = row.GetPersonIndex();

                CurrentPerson = CurrentDeclarant;
                CurrentPerson.document_position = row.NameDocPosition;
                CurrentPerson.sheet_index = _Declaration.Properties.SheetNumber;
                _Declaration.PublicServants.Add(CurrentDeclarant);
            }

            public void CreateNewRelative(DataRow row)
            {
                Logger.Debug("Relative {0} at row {1}", row.RelativeType, row.GetRowIndex());
                if (CurrentDeclarant == null)
                {
                    if (FailOnRelativeOrphan)
                    {
                        throw new SmartParserRelativeWithoutPersonException(
                            string.Format("Relative {0} at row {1} without main Person", row.RelativeType, row.GetRowIndex()));
                    }
                    else
                    {
                        return;
                    }
                }
                Relative relative = new Relative();
                CurrentDeclarant.AddRelative(relative);
                CurrentPerson = relative;

                RelationType relationType = DataHelper.ParseRelationType(row.RelativeType, false);
                    if (relationType == RelationType.Error)
                {
                    throw new SmartParserException(
                        string.Format("Wrong relative name '{0}' at row {1} ", row.RelativeType, row));
                }
                relative.RelationType = relationType;
                relative.document_position = row.NameDocPosition;
                relative.sheet_index = _Declaration.Properties.SheetNumber;
            }

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

            bool fieldInThousands = (field & DeclarationField.DeclaredYearlyIncomeThousands) > 0;
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
