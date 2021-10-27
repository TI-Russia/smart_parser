using StringHelpers;
using SmartParser.Lib;

using System;
using System.Collections.Generic;
using System.Linq;


namespace SmartParser.Lib
{
    class TBorderFinder
    {
        IAdapter Adapter = null;
        DeclarationSection CurrentSection = null;
        PublicServant CurrentDeclarant = null;
        public Person CurrentPerson = null;
        Declaration _Declaration;
        bool FailOnRelativeOrphan;

        public TBorderFinder(IAdapter adapter, Declaration declaration, bool failOnRelativeOrphan)
        {
            Adapter = adapter;
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
        static public List<string> GetLinesWithSoftBreaks(Cell cell)
        {
            if (cell.FontSize == 0)
            {
                return cell.Text.Split('\n').ToList<string>();
            }
            else
            {
                TStringMeasure.InitDefaultFont(cell.FontName, cell.FontSize);
                return TStringMeasure.GetLinesBySoftBreaks(cell.Text, cell.CellWidth);
            }
        }

        void DivideCell(DataRow inputRow, int cellIndex, List<int> borders, List<DataRow> dividedLines)
        {
            var divided = GetLinesWithSoftBreaks(inputRow.Cells[cellIndex]);
            List<String> notEmptyLines = new List<String>();
            String lastLine = "";
            foreach (var s in divided)
            {
                if (!s.IsNullOrWhiteSpace())
                {
                    if (lastLine.IsNullOrWhiteSpace())
                    {
                        notEmptyLines.Add(s);
                    }
                    else
                    {
                        notEmptyLines[notEmptyLines.Count() - 1] += "\n" + s;
                    }
                }
                lastLine = s;
            }
            if (notEmptyLines.Count == borders.Count)
            {
                for (int k = 0; k < borders.Count; ++k)
                {
                    dividedLines[k].Cells[cellIndex].Text = notEmptyLines[k];
                    dividedLines[k].Cells[cellIndex].IsEmpty = false;
                }
            }
            else
            {
                int start = 0;
                for (int k = 0; k < borders.Count; ++k)
                {
                    int end = (k + 1 == borders.Count) ? divided.Count : borders[k + 1];
                    if (start < divided.Count)
                    {
                        string value = String.Join("\n", divided.Skip(start).Take(end - start));
                        if (value.Length > 0)
                        {
                            dividedLines[k].Cells[cellIndex].Text = value;
                            dividedLines[k].Cells[cellIndex].IsEmpty = false;
                        }
                    }
                    start = end;
                }
            }
        }
        bool DividedLinesToDataRows(DataRow inputRow, List<DataRow> dividedLines, int lineIndex)
        {
            DataRow currRow = dividedLines[lineIndex];
            var nameOrRelativeType = currRow.GetDeclarationField(DeclarationField.NameOrRelativeType).Text.Replace("не имеет", "");
            if (lineIndex == 0)
            {
                currRow.PersonName = nameOrRelativeType;
                currRow.Occupation = inputRow.Occupation.Replace("не имеет", "");
                currRow.Department = inputRow.Department;
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
            CurrentPerson.DateRows.Add(dividedLines[lineIndex]);
            return true;
        }

        //  see 8562.pdf.docx  in tests
        //  calc string width using graphics.MeasureString methods
        bool DivideDeclarantAndRelativesBySoftEolns(TableHeader columnOrdering, DataRow row)
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
            List<string> lines = GetLinesWithSoftBreaks(nameCell);
            if (lines.Count < 2) return false;
            List<int> borders = new List<int>() { 0 };

            for (int i = 1; i < lines.Count; ++i)
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
                DivideCell(row, i, borders, dividedLines);
            }
            for (int k = 0; k < borders.Count; ++k)
            {
                if (!DividedLinesToDataRows(row, dividedLines, k))
                {
                    return false;
                }
            }
            Logger.Debug(String.Format("Divide line to {0} parts", borders.Count()));
            return true;
        }
        public void AddInputRowToCurrentPerson(TableHeader columnOrdering, DataRow row)
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

        void CopyRelativeFieldToMainCell(DataRow row, DeclarationField relativeMask, DeclarationField f, ref DataRow childRow)
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
        public void TransposeTableByRelatives(TableHeader columnOrdering, DataRow row)
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
            CurrentDeclarant.NameRaw = row.PersonName.RemoveStupidTranslit().Replace("не имеет", "").NormSpaces().Trim();
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
            Logger.Debug(String.Format("Relative {0} at row {1}", row.RelativeType, row.GetRowIndex()));
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

        bool IsHeaderRow(DataRow row, out TableHeader columnOrdering)
        {
            columnOrdering = null;
            if (!TableHeaderRecognizer.WeakHeaderCheck(Adapter, row.Cells))
                return false;
            try
            {
                columnOrdering = new TableHeader();
                TableHeaderRecognizer.ReadHeader(Adapter, row.GetRowIndex(), columnOrdering);
                return true;
            }
            catch (Exception e)
            {
                Logger.Debug(String.Format("Cannot parse possible header, row={0}, error={1}, so skip it may be it is a data row ", e.ToString(), row.GetRowIndex()));
            }
            return false;
        }

        public void FindBordersAndPersonNames(TableHeader columnOrdering, bool updateTrigrams)
        {
            int rowOffset = columnOrdering.FirstDataRow;
            if (columnOrdering.Section != null)
            {
                CreateNewSection(rowOffset, columnOrdering.Section);
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
                Logger.Debug(String.Format("currRow {0}, col_count={1}: {2}", row, currRow.Cells.Count, currRow.DebugString()));

                string sectionName;
                if (Adapter.IsSectionRow(row, currRow.Cells, columnOrdering.GetMaxColumnEndIndex(), false, out sectionName))
                {
                    CreateNewSection(row, sectionName);
                    continue;
                }
                {
                    TableHeader newColumnOrdering;
                    if (IsHeaderRow(currRow, out newColumnOrdering))
                    {
                        columnOrdering = newColumnOrdering;
                        Logger.Debug(String.Format("found a new table header {0}", currRow.DebugString()));
                        row = newColumnOrdering.GetPossibleHeaderEnd() - 1; // row++ in "for" cycle
                        continue;
                    }
                }

                if (updateTrigrams) ColumnByDataPredictor.UpdateByRow(columnOrdering, currRow);

                if (!currRow.InitPersonData(prevPersonName))
                {
                    // be robust, ignore errors see 8562.pdf.docx in tests
                    continue;
                }

                if (currRow.PersonName != String.Empty)
                {
                    prevPersonName = currRow.PersonName;
                    CreateNewDeclarant(Adapter, currRow);
                    if (CurrentPerson != null)
                        skipEmptyPerson = false;
                }
                else if (currRow.RelativeType != String.Empty)
                {
                    if (!skipEmptyPerson)
                    {
                        try
                        {
                            CreateNewRelative(currRow);
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
                    if (CurrentPerson == null && FailOnRelativeOrphan)
                    {
                        skipEmptyPerson = true;
                        Logger.Error(String.Format("No person to attach info on row={0}", row));
                        continue;
                    }
                }
                if (!skipEmptyPerson)
                {
                    AddInputRowToCurrentPerson(columnOrdering, currRow);
                    if (_Declaration.Properties.Year == null && columnOrdering.ContainsField(DeclarationField.IncomeYear))
                    {
                        var incomeYear = currRow.GetDeclarationField(DeclarationField.IncomeYear);
                        if (incomeYear != null)
                        {
                            _Declaration.Properties.Year = int.Parse(incomeYear.Text);
                        }
                    }
                }

            }
            if (updateTrigrams) ColumnByDataPredictor.WriteData();

            Logger.Info("Parsed {0} declarants", _Declaration.PublicServants.Count());

        }
    }
}