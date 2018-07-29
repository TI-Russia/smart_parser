using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Lib
{
    static public class PropertyDictionary
    {
        static public Dictionary<String, RealEstateType> PropertyTypes { get; set;  } = LoadPropertyDictionary();


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
        static Dictionary<String, RealEstateType> LoadPropertyDictionary()
        {
            Dictionary<String, RealEstateType> propertyTypes = new Dictionary<String, RealEstateType>();

            foreach (var l in GetResource())
            {
                string[] keyvalue = l.Split(new string[] { "=>" }, StringSplitOptions.None);
                RealEstateType value = (RealEstateType)Enum.Parse(typeof(RealEstateType), keyvalue[1]);
                propertyTypes.Add(keyvalue[0], value);
            }
            return propertyTypes;
        }

    }
}
