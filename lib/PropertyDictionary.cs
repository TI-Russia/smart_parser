using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    static public class PropertyDictionary
    {
        static public Dictionary<String, RealEstateType> PropertyTypes { get; set; }
        static public List<Tuple<Regex, RealEstateType>> PropertyTypesRegex { get; set; }

        static PropertyDictionary()
        {
            LoadPropertyDictionary();
        }

        static List<string> GetResource()
        {
            List<string> lines = new List<string>();
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.PropertyDictionary.txt"))
            using (var reader = new StreamReader(stream))
            {
                while (!reader.EndOfStream)
                {
                    lines.Add(reader.ReadLine());
                }
            }
            return lines;
        }
        static void LoadPropertyDictionary()
        {
            PropertyTypes = new Dictionary<String, RealEstateType>();
            PropertyTypesRegex = new List<Tuple<Regex, RealEstateType>>();

            foreach (var l in GetResource())
            {
                if (l.StartsWith("#") || l.IsNullOrWhiteSpace())
                {
                    continue;
                }

                string[] keyvalue = l.Split(new string[] { "=>" }, StringSplitOptions.None);
                RealEstateType value = (RealEstateType)Enum.Parse(typeof(RealEstateType), keyvalue[1]);

                string key = keyvalue[0];
                if (key.StartsWith("Regex:"))
                {
                    string reg = key.Substring("Regex:".Length);
                    PropertyTypesRegex.Add(Tuple.Create(new Regex(reg, RegexOptions.Compiled), value));
                }
                else
                {
                    PropertyTypes.Add(key, value);
                }

            }
        }

        public static bool ParseParseRealEstateType(string strType, out RealEstateType type)
        {
            
            if (PropertyTypes.TryGetValue(strType, out type))
            {
                return true;
            }
            foreach (var t in PropertyTypesRegex)
            {
                if (t.Item1.IsMatch(strType))
                {
                    type = t.Item2;
                    return true;
                }
            }
            return false;
        }

    }
}
