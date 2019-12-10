using System;
using System.Collections.Generic;
using System.Text;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Reflection;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;


namespace Parser.Lib
{
    using TrigramsDict = Dictionary<DeclarationField, Dictionary<string, int>>;
    public class ColumnPredictor
    {
        static  TrigramsDict Trigrams = new TrigramsDict();
        static Dictionary<DeclarationField, double> ClassFreq;
        static double SampleLen;
        static public bool CalcPrecision =  false;
        static public int CorrectCount = 0;
        static public int AllCount = 0;


        //static ColumnPredictor() //do not know why static constructor is not called,use Initialize
        public static void InitializeIfNotAlready()
        {
            if (SampleLen == 0)
            {
                ReadData();
                BuildClassFreqs();
            }
        }

        static string GetDataPath()
        {
            string executableLocation = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            return Path.Combine(executableLocation, "column_trigrams.txt");
        }
        public static void ReadData()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.column_trigrams.txt"))
            {
                using (var file = new System.IO.StreamReader(stream))
                {
                    string jsonStr = file.ReadToEnd();
                    Trigrams = JsonConvert.DeserializeObject<TrigramsDict>(jsonStr);
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
            if (    ((field & DeclarationField.StartsWithDigitMask) > 0)
                 && !Char.IsNumber(text[0]))
            {
                    return false;
            }
            if (    DataHelper.IsCountryStrict(text)
                &&  (field & DeclarationField.CountryMask) == 0)
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
            var fields = new List <DeclarationField > (freqs.Keys);
            foreach (var trigram in String2Trigrams(words))
            {
                foreach  (var field in fields)
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
            foreach (string w in words) {
                if (DataHelper.IsEmptyValue(w)) continue;
                var f = PredictByString(w);
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
            var predictedField = ColumnPredictor.PredictByString(text);
            return (predictedField & ~DeclarationField.AllOwnTypes) == (field & ~DeclarationField.AllOwnTypes);
        }


        public static void WriteData()
        {
            using (var file = new System.IO.StreamWriter(GetDataPath()))
            {
                file.WriteLine(JsonConvert.SerializeObject(Trigrams));
            }
        }

        public static void IncrementTrigrams(DeclarationField field,  string words)
        {
            if (!Trigrams.ContainsKey(field) )
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
        public static void UpdateByRow(ColumnOrdering columnOrdering, DataRow row)
        {
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
        public static DeclarationField PredictEmptyColumnTitle(IAdapter adapter, Cell headerCell)
        {
            List<string> texts = new List<string>();
            int rowIndex = headerCell.Row + headerCell.MergedRowsCount;
            const int maxRowToCollect = 10;
            for (int i = 0; i < maxRowToCollect; i++)
            {
                var cells = adapter.GetCells(rowIndex, IAdapter.MaxColumnsCount);
                string dummy;
                if (IAdapter.IsSectionRow(cells, adapter.GetColsCount(), false, out dummy))
                {
                    rowIndex += 1;
                }
                else
                {
                    var c = adapter.GetCell(rowIndex, headerCell.Col);
                    if (c != null)
                    {
                        texts.Add(c.GetText(true));
                        rowIndex += c.MergedRowsCount;
                    }
                    else
                    {
                        rowIndex += 1;
                    }
                }
                if (rowIndex >= adapter.GetRowsCount()) break;
            }
            var field = PredictByStrings(texts);
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
