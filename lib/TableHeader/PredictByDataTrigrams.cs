using StringHelpers;
using SmartParser.Lib;

using System;
using System.Collections.Generic;
using System.Text;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Reflection;
using Newtonsoft.Json;
using System.Linq;
using System.Text.RegularExpressions;


namespace SmartParser.Lib
{
    using TrigramsDict = Dictionary<DeclarationField, Dictionary<string, int>>;
    public class ColumnByDataPredictor
    {
        static TrigramsDict Trigrams = new TrigramsDict();
        static Dictionary<DeclarationField, double> ClassFreq;
        static double SampleLen;
        static public bool CalcPrecision = false;
        static public int CorrectCount = 0;
        static public int AllCount = 0;
        static string ExternalFileName = null;


        public static void InitializeIfNotAlready(string fileName = null)
        {
            if (SampleLen == 0)
            {
                if (fileName == null)
                {
                    ReadDataFromAssembly();
                }
                else
                {
                    ReadDataFromExternalFile(fileName);
                }
                BuildClassFreqs();
            }
        }

        public static void ReadDataFromExternalFile(string fileName)
        {
            ExternalFileName = fileName;
            using (StreamReader stream = new StreamReader(fileName))
            {
                Trigrams = JsonConvert.DeserializeObject<TrigramsDict>(stream.ReadToEnd());
            }
            Logger.Info(String.Format("Read trigrams for {0} declaration fields", Trigrams.Count));
        }
        public static void ReadDataFromAssembly()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            var debug = Assembly.GetExecutingAssembly().GetManifestResourceNames();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.column_trigrams.txt"))
            {
                using (var file = new System.IO.StreamReader(stream))
                {
                    Trigrams = JsonConvert.DeserializeObject<TrigramsDict>(file.ReadToEnd());
                }
            }
        }
        public static System.Collections.Generic.IEnumerable<string> String2Trigrams(string words)
        {
            words = "^" + words.ReplaceEolnWithSpace().CoalesceWhitespace() + "$";
            for (int i = 0; i < words.Length - 2; i++)
            {
                yield return words.Substring(i, 3);
            }
        }

        static void BuildClassFreqs()
        {
            SampleLen = 0;
            ClassFreq = new Dictionary<DeclarationField, double>();
            foreach (var i in Trigrams)
            {
                ClassFreq[i.Key] = 0;
                foreach (var j in i.Value)
                {
                    ClassFreq[i.Key] += j.Value;
                    SampleLen += j.Value;
                }
            }
        }

        static DeclarationField FindMin(Dictionary<DeclarationField, double> freqs)
        {
            // Linq is slower
            double minValue = Double.MaxValue;
            DeclarationField resultField = DeclarationField.None;
            foreach (var i in freqs)
            {
                if (i.Value < minValue)
                {
                    minValue = i.Value;
                    resultField = i.Key;
                }
            }
            return resultField;
        }

        static bool TestFieldRegexpWeak(DeclarationField field, string text)
        {
            if (text.Length == 0) return true;
            if (text == "п/п" && field == DeclarationField.DeclarantIndex) return true;
            if (((field & DeclarationField.StartsWithDigitMask) > 0)
                 && !Char.IsNumber(text[0]))
            {
                return false;
            }
            if (DataHelper.IsCountryStrict(text)
                && (field & DeclarationField.CountryMask) == 0)
            {
                return false;
            }
            return true;

        }


        // follow https://habr.com/ru/post/120194/
        public static DeclarationField PredictByString(string words)
        {
            Debug.Assert(SampleLen > 0);
            var freqs = new Dictionary<DeclarationField, double>();
            foreach (var i in Trigrams)
            {
                if (TestFieldRegexpWeak(i.Key, words))
                    freqs[i.Key] = -Math.Log(ClassFreq[i.Key] / SampleLen);
            }
            var fields = new List<DeclarationField>(freqs.Keys);
            foreach (var trigram in String2Trigrams(words))
            {
                foreach (var field in fields)
                {
                    //DeclarationField field = i.Key;
                    int freq = 0;
                    Trigrams[field].TryGetValue(trigram, out freq);
                    double trigramProb = ((double)freq + 10E-10) / ClassFreq[field];
                    freqs[field] += -Math.Log(trigramProb);
                }
            }
            return FindMin(freqs);
        }

        public static DeclarationField PredictByStrings(List<string> words)
        {
            var negativeFreqs = new Dictionary<DeclarationField, double>();
            foreach (string w in words)
            {
                if (DataHelper.IsEmptyValue(w)) continue;
                var f = HeaderHelpers.TryGetField("", w);
                if (f == DeclarationField.None)
                {
                    f = PredictByString(w);
                }
                if (negativeFreqs.ContainsKey(f))
                {
                    negativeFreqs[f] -= 1;
                }
                else
                {
                    negativeFreqs[f] = -1;
                }
            }
            return FindMin(negativeFreqs);
        }

        public static bool TestFieldWithoutOwntypes(DeclarationField field, Cell cell)
        {
            if (cell.IsEmpty) return false;
            string text = cell.GetText(true);
            if ((field & DeclarationField.SquareMask) > 0 && DataHelper.ParseSquare(text).HasValue)
            {
                return true;
            }

            var predictedField = ColumnByDataPredictor.PredictByString(text);
            return (predictedField & ~DeclarationField.AllOwnTypes) == (field & ~DeclarationField.AllOwnTypes);
        }


        public static void WriteData()
        {
            Logger.Info(String.Format("write trigrams to {0}", ExternalFileName));
            using (var file = new System.IO.StreamWriter(ExternalFileName))
            {
                file.WriteLine(JsonConvert.SerializeObject(Trigrams));
            }
        }

        public static void IncrementTrigrams(DeclarationField field, string words)
        {
            if (!Trigrams.ContainsKey(field))
            {
                Trigrams[field] = new Dictionary<string, int>();
            }
            var FieldTrigrams = Trigrams[field];
            foreach (var trigram in String2Trigrams(words))
            {
                if (!FieldTrigrams.ContainsKey(trigram))
                {
                    FieldTrigrams[trigram] = 1;
                }
                else
                {
                    FieldTrigrams[trigram] = FieldTrigrams[trigram] + 1;
                }
            }
        }
        public static void UpdateByRow(TableHeader columnOrdering, DataRow row)
        {
            // otherwize nowhere to write
            Debug.Assert(ColumnByDataPredictor.ExternalFileName != null);

            foreach (var i in columnOrdering.MergedColumnOrder)
            {
                try
                {
                    var cell = row.GetDeclarationField(i.Field);
                    var s = (cell == null) ? "" : cell.GetText();
                    IncrementTrigrams(i.Field, s);
                }
                catch (Exception)
                {

                }
            }
        }
        public static string GetPrecisionStr()
        {
            return String.Format(
                    "Predictor precision all={0} correct={1}, precision={2}",
                    AllCount, CorrectCount,
                    CorrectCount / ((double)AllCount + 10E-10));
        }

        // попытка предсказать заголовок колонки по данным внутри таблицы. В случае, когда название колонки слишком расплывчато
        public static DeclarationField PredictGenericColumnTitle(IAdapter adapter, Cell headerCell)
        {
            var field = DeclarationField.None;
            int maxRowToCollect = Math.Min(50, adapter.GetRowsCount());
            List<string> texts = new List<string>();
            var possible = 0;
            var not_possible = 0;

            var possibleFields = new List<DeclarationField>();

            int rowIndex = headerCell.Row + headerCell.MergedRowsCount;
            for (int i = 0; i < maxRowToCollect; i++)
            {
                var index = rowIndex + i;
                var cells = adapter.GetDataCells(index, IAdapter.MaxColumnsCount);
                var c = cells.Count > headerCell.Col ? cells[headerCell.Col] : null;
                if (c == null)
                {
                    continue;
                }
                var txt = c.GetText(true);
                if (!string.IsNullOrWhiteSpace(txt))
                {

                    if (Regex.IsMatch(txt, "(МСЧ|КБ|ЦКБ|ФНКЦ|ГНЦ|ФМБЦ)"))
                    {
                        possibleFields.Add(DeclarationField.Department);
                        possible++;
                    }
                    else
                    {
                        possibleFields.Add(DeclarationField.None);
                    }
                }
            }

            return possibleFields.Count > 0 ? possibleFields.GroupBy(v => v).OrderByDescending(g => g.Count()).First().Key : DeclarationField.None;

        }
        public static DeclarationField PredictEmptyColumnTitle(IAdapter adapter, Cell headerCell)
        {
            List<string> texts = new List<string>();
            int rowIndex = headerCell.Row + headerCell.MergedRowsCount;
            const int maxRowToCollect = 10;
            int numbers = 0;
            int not_numbers = 0;
            for (int i = 0; i < maxRowToCollect; i++)
            {
                var cells = adapter.GetDataCells(rowIndex, IAdapter.MaxColumnsCount);
                string dummy;
                if (adapter.IsSectionRow(rowIndex, cells, adapter.GetColsCount(), false, out dummy))
                {
                    rowIndex += 1;
                }
                else if (IAdapter.IsNumbersRow(cells))
                {
                    rowIndex += 1;
                }
                else
                {
                    var c = adapter.GetCell(rowIndex, headerCell.Col);
                    if (c != null)
                    {
                        var txt = c.GetText(true);
                        if (txt.Length > 0)
                        {
                            texts.Add(txt);
                            int d;
                            if (int.TryParse(txt, out d))
                            {
                                numbers += 1;
                            }
                            else
                            {
                                not_numbers += 1;
                            }
                        }
                        rowIndex += c.MergedRowsCount;
                    }
                    else
                    {
                        rowIndex += 1;
                    }
                }
                if (rowIndex >= adapter.GetRowsCount()) break;
            }
            var field = DeclarationField.None;
            if (texts.Count == 1 && headerCell.Col == 0 && TextHelpers.CanBePatronymic(texts[0]))
            {
                // not enough data, if texts.Count == 1
                field = DeclarationField.NameOrRelativeType;
            }
            else if (headerCell.Col == 0 && numbers > not_numbers)
            {
                field = DeclarationField.DeclarantIndex;
            }
            else
            {
                field = PredictByStrings(texts);
                if (field == DeclarationField.NameOrRelativeType && String.Join(" ", texts).Contains(","))
                {
                    field = DeclarationField.NameAndOccupationOrRelativeType;
                }
            }

            if (headerCell.TextAbove != null && ((field & DeclarationField.AllOwnTypes) > 0))
            {
                string h = headerCell.TextAbove;
                // AllOwnTypes defined from 
                field &= ~DeclarationField.AllOwnTypes;
                if (HeaderHelpers.IsMixedColumn(h))
                {
                    field |= DeclarationField.Mixed;
                }
                else if (HeaderHelpers.IsStateColumn(h))
                {
                    field |= DeclarationField.State;
                }
                else if (HeaderHelpers.IsOwnedColumn(h))
                {
                    field |= DeclarationField.Owned;
                }
            }
            if (field == DeclarationField.NameOrRelativeType)
            {
                if (TextHelpers.MayContainsRole(String.Join(" ", texts)))
                {
                    field = DeclarationField.NameAndOccupationOrRelativeType;
                }
            }
            Logger.Debug(string.Format("predict by {0}  -> {1}",
                String.Join("\\n", texts), field));
            return field;
        }
        public static void PredictForPrecisionCheck(IAdapter adapter, Cell headerCell, DeclarationField field)
        {
            var predicted_field = PredictEmptyColumnTitle(adapter, headerCell);
            if (predicted_field == field)
            {
                CorrectCount += 1;
            }
            else
            {
                Logger.Debug(
                    string.Format("wrong predicted as {0} must be {1} ",
                    predicted_field, field));

            }
            AllCount += 1;
        }
    }
}
