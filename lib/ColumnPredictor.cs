using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Reflection;
using TI.Declarator.ParserCommon;
using Newtonsoft.Json;
using Smart.Parser.Adapters;


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
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.column_trigrams.txt"))
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

        // follow https://habr.com/ru/post/120194/
        public static DeclarationField ClassifyString(string words)
        {
            Debug.Assert(SampleLen > 0);
            var freqs = new Dictionary<DeclarationField, double>();
            foreach (var i in Trigrams)
            {
                freqs[i.Key] = -Math.Log(ClassFreq[i.Key] / SampleLen);
            }
            foreach (var trigram in String2Trigrams(words))
            {
                foreach  (var i in Trigrams)
                {
                    DeclarationField field = i.Key;
                    int freq = 0;
                    i.Value.TryGetValue(trigram, out freq);
                    double trigramProb = ((double)freq + 10E-10) / ClassFreq[field];
                    freqs[field] += -Math.Log(trigramProb);
                }
            }
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
        public static DeclarationField ClassifyStrings(List<string> words)
        {
           return ClassifyString(String.Join("$^", words));
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
    }
}
