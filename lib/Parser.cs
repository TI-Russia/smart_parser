using Parser.Lib;
using Smart.Parser.Adapters;
using System;
using System.Threading;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using TI.Declarator.ParserCommon;
using System.Globalization;

namespace Smart.Parser.Lib
{
    
    public class Parser
    {
        DateTime FirstPassStartTime;
        DateTime SecondPassStartTime;
        bool FailOnRelativeOrphan;
        static readonly string OwnedString = "В собственности";
        static readonly string StateString = "В пользовании";
        static NumberFormatInfo ParserNumberFormatInfo = new NumberFormatInfo();
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

        Declaration InitializeDeclaration(ColumnOrdering columnOrdering, int? user_documentfile_id)
        {
            // parse filename
            int? documentfile_id;
            string archive;
            bool result = DataHelper.ParseDocumentFileName(Adapter.DocumentFile, out documentfile_id, out archive);
            if (user_documentfile_id.HasValue)
                documentfile_id = user_documentfile_id;

            DeclarationProperties properties = new DeclarationProperties()
            {
                Title = columnOrdering.Title,
                MinistryName = columnOrdering.MinistryName,
                Year = columnOrdering.Year,
                SheetName = Adapter.GetWorksheetName(),
                documentfile_id = documentfile_id,
                archive_file = archive,
                sheet_number = Adapter.GetWorksheetIndex()
            };
            if (properties.Year == null)
            {
                properties.Year = columnOrdering.YearFromIncome;
            }
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
                _Declaration.Sections.Add(CurrentSection);

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
                if (nameCell.FontSize == 0) return false; // no font info
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
                    var nameOrRelativeType = currRow.GetDeclarationField(DeclarationField.NameOrRelativeType).Text;
                    if (k == 0)
                    {
                        currRow.PersonName = nameOrRelativeType;
                        currRow.Occupation = row.Occupation;
                        currRow.Department = row.Department;

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
                CurrentDeclarant.NameRaw = row.PersonName;
                CurrentDeclarant.Occupation = row.Occupation;
                CurrentDeclarant.Department = row.Department;
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
                _Declaration.PublicServants.Add(CurrentDeclarant);
            }

            public void CreateNewRelative(DataRow row)
            {
                Logger.Debug("Relative {0} at row {1}", row.RelativeType, row.GetRowIndex());
                if (CurrentDeclarant == null)
                {
                    if (FailOnRelativeOrphan)
                    {
                        throw new SmartParserException(
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
            }

        }

        bool IsNumbersRow(DataRow row)
        {
            string s = "";
            foreach (var c in row.Cells)
            {
                s += c.Text.Replace("\n", "").Replace(" ", "") + " ";
            }

            if (s.StartsWith("1 2 3 4"))
                return true;

            return false;
        }

        bool IsHeaderRow(DataRow row, out ColumnOrdering columnOrdering)
        {
            columnOrdering = null;
            if (!ColumnDetector.WeakHeaderCheck(row.Cells)) return false;
            try
            {
                columnOrdering = new ColumnOrdering();
                ColumnDetector.ReadHeader(Adapter, row.GetRowIndex(), columnOrdering);
                return true;
            }
            catch (Exception e)
            {
                Logger.Error(String.Format("Cannot parse possible header, row={0}, error={1}, so skip it may be it is a data row ", e.ToString(), row.GetRowIndex()));

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
            

            for (int row = rowOffset; row < Adapter.GetRowsCount(); row++)
            {
                DataRow currRow = Adapter.GetRow(columnOrdering, row);
                if (currRow == null || currRow.IsEmpty())
                {
                    continue;
                }
                if (IsNumbersRow(currRow))
                {
                    continue;
                }
                Logger.Debug(currRow.DebugString());

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

                if (!currRow.InitPersonData())
                {
                    // be robust, ignore errors see 8562.pdf.docx in tests
                    continue;
                }

                if (currRow.PersonName != String.Empty)
                {
                    borderFinder.CreateNewDeclarant(Adapter, currRow);
                }
                else if  (currRow.RelativeType !=  String.Empty)
                {
                    borderFinder.CreateNewRelative(currRow);
                }
                else 
                {
                    if (borderFinder.CurrentPerson == null && FailOnRelativeOrphan)
                    {
                        throw new SmartParserException("No person to attach info");
                    }
                }
                borderFinder.AddInputRowToCurrentPerson(columnOrdering, currRow);
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
                        ParseIncome(row, dummy, true);
                        if (dummy.DeclaredYearlyIncome != null)
                        {
                            incomes.Add(dummy.DeclaredYearlyIncome.Value);
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
                    declaration.IgnoreThousandMultipler = true;
                }
            }
        }

        public static void CheckProperty(RealEstateProperty prop)
        {
            if (prop == null)
            {
                return;
            }

            if (String.IsNullOrEmpty(prop.country_raw))
            {
                //Logger.Error(CurrentRow, "wrong country: {0}", prop.country_raw);
            }
        }

        void AddRealEstateWithNaturalText (DataRow currRow, DeclarationField fieldName, string ownTypeByColumn, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(fieldName))
            {
                fieldName = fieldName | DeclarationField.MainDeclarant;
            }

            if (currRow.ColumnOrdering.ContainsField(fieldName))
            {
                RealEstateProperty realEstateProperty = new RealEstateProperty();
                realEstateProperty.Text = currRow.GetContents(fieldName).Trim();
                if (!DataHelper.IsEmptyValue(realEstateProperty.Text))
                {
                    realEstateProperty.own_type_by_column = ownTypeByColumn;
                    CheckProperty(realEstateProperty);
                    person.RealEstateProperties.Add(realEstateProperty);
                }
            }

            

        }
        public void ParseOwnedProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.OwnedRealEstateSquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.OwnedColumnWithNaturalText, OwnedString, person);
                return;
            }
            string estateTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateType);
            string ownTypeStr = null;
            if (currRow.ColumnOrdering.OwnershipTypeInSeparateField)
            {
                ownTypeStr = currRow.GetContents(DeclarationField.OwnedRealEstateOwnershipType);
            }
            string squareStr = currRow.GetContents(DeclarationField.OwnedRealEstateSquare);
            string countryStr = currRow.GetContents(DeclarationField.OwnedRealEstateCountry, false);

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

        public void ParseMixedProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.MixedRealEstateSquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.MixedColumnWithNaturalText, null, person);
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

        public void ParseStateProperty(DataRow currRow, Person person)
        {
            if (!currRow.ColumnOrdering.ContainsField(DeclarationField.StatePropertySquare))
            {
                AddRealEstateWithNaturalText(currRow, DeclarationField.StateColumnWithNaturalText, StateString, person);
                return;
            }
            string statePropTypeStr = currRow.GetContents(DeclarationField.StatePropertyType);
            string statePropSquareStr = currRow.GetContents(DeclarationField.StatePropertySquare);
            string statePropCountryStr = currRow.GetContents(DeclarationField.StatePropertyCountry, false);

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
        bool ParseIncomeOneField(DataRow currRow, Person person, DeclarationField field, bool ignoreThousandMultiplier)
        {
            if (!currRow.ColumnOrdering.ContainsField(field)) return false;
            string fieldStr = currRow.GetContents(field);
            if (fieldStr == "") return false;
            bool fieldInThousands = (field & DeclarationField.DeclaredYearlyIncomeThousands) > 0;
            person.DeclaredYearlyIncome = DataHelper.ParseDeclaredIncome(fieldStr, fieldInThousands);
            if (!ignoreThousandMultiplier)
            {
                person.DeclaredYearlyIncome *= 1000;
            }
            if (!DataHelper.IsEmptyValue(fieldStr))
                person.DeclaredYearlyIncomeRaw = NormalizeRawDecimalForTest(fieldStr);
            return true;
        }
        bool ParseIncome(DataRow currRow, Person person, bool ignoreThousandMultiplier)
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

        public Declaration ParsePersonalProperties(Declaration declaration)
        {
            ForgetThousandMultiplier(declaration);
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
                        Logger.Debug(((PublicServant)person).NameRaw.ReplaceEolnWithSpace());
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
                                DeclarationField.NameOrRelativeType))
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
                        CurrentRow = currRow.GetRowIndex();
            
                        if (!foundIncomeInfo)
                        {
                            if (ParseIncome(currRow, person, declaration.IgnoreThousandMultipler))
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
                var s = r.GetContents(DeclarationField.Vehicle);
                if (!DataHelper.IsEmptyValue(s))
                    person.Vehicles.Add(new Vehicle(s));
            }
            else if (r.ColumnOrdering.ColumnOrder.ContainsKey(DeclarationField.DeclarantVehicle))
            {
                var s = r.GetContents(DeclarationField.DeclarantVehicle);
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
        
        static string NormalizeRawDecimalForTest(string s)
        {
            Double v;
            if (Double.TryParse(s, out v))
            {
                return v.ToString(ParserNumberFormatInfo);
            }
            else
            {
                return s.Replace(".", ",").Replace("\u202f", " ");
                //return s;
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
            stateProperty.square_raw = NormalizeRawDecimalForTest(statePropSquareStr);
            stateProperty.country_raw = DataHelper.ParseCountry(statePropCountryStr);
            stateProperty.own_type_by_column = StateString;
            CheckProperty(stateProperty);
            person.RealEstateProperties.Add(stateProperty);
        }

        static public void ParseOwnedPropertySingleRow(string estateTypeStr, string ownTypeStr, string areaStr, string countryStr, Person person)
        {
            estateTypeStr = estateTypeStr.Trim();
            areaStr = areaStr.ReplaceEolnWithSpace();
            if (DataHelper.IsEmptyValue(estateTypeStr))
            {
                return;
            }

            RealEstateProperty realEstateProperty = new RealEstateProperty();

            realEstateProperty.square = DataHelper.ParseSquare(areaStr);
            realEstateProperty.square_raw = NormalizeRawDecimalForTest(areaStr);
            realEstateProperty.country_raw = DataHelper.ParseCountry(countryStr);

            // колонка с типом недвижимости отдельно
            if (ownTypeStr != null)
            {
                realEstateProperty.type_raw = estateTypeStr;
                realEstateProperty.own_type_raw = ownTypeStr;
                realEstateProperty.own_type_by_column = OwnedString;
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
            return  String.Join("\n", lines.Skip(start).Take(end - start)).ReplaceEolnWithSpace();
        }

        static List<string> DivideByBordersOrEmptyLines(string value, List<int> linesWithNumbers)
        {
            var result = new List<string>();
            if (value == null)
            {
                return result;
            }
            string[] lines = value.Trim(' ', ';').Split(';');
            if (lines.Length != linesWithNumbers.Count) {
                lines = value.Split('\n');
            }
            Debug.Assert(linesWithNumbers.Count > 1);
            int startLine = linesWithNumbers[0];
            int numberIndex = 1;
            string item;
            for (int i = startLine + 1; i < lines.Count(); ++i)
            {
                item = SliceArrayAndTrim(lines, startLine, i);
                if (item.Count() > 0) // not empty item
                {
                    if ((numberIndex < linesWithNumbers.Count && i == linesWithNumbers[numberIndex]) || lines[i].Trim().Count() == 0)
                    {
                        result.Add(item);
                        startLine = i;
                        numberIndex++;
                    }
                }
            }

            item = SliceArrayAndTrim(lines, startLine, lines.Count());
            if (item.Count() > 0) result.Add(item);

            if (result.Count < linesWithNumbers.Count) {
                var notEmptyLines = new List<string>();
                foreach (var l in lines) {
                    if (l.Trim(' ').Length > 0) {
                        notEmptyLines.Add(l);
                    }
                }
                if (notEmptyLines.Count == linesWithNumbers.Count) {
                    return notEmptyLines;
                }
            }
    
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
        static int CurrentRow { get; set; } = -1;

        
    }
}
