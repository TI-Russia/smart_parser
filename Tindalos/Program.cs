using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.Office.Interop.Word;

using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;
using TI.Declarator.WordParser;

namespace Tindalos
{
    class Tindalos
    {
        private static Dictionary<String, RealEstateType> PropertyTypes = new Dictionary<string, RealEstateType>();

        static Tindalos()
        {
            foreach (var l in File.ReadAllLines("PropertyDictionary.txt"))
            {
                string[] keyvalue = l.Split(new string[] { "=>" }, StringSplitOptions.None);
                RealEstateType value = (RealEstateType)Enum.Parse(typeof(RealEstateType), keyvalue[1]);
                PropertyTypes.Add(keyvalue[0], value);
            }
        }

        static void Main(string[] args)
        {
            //var parser = new DocXParser();
            //parser.Parse("2016_Sotrudniki_ministerstva.docx");            

            string sourceFile = "2016_Rukovoditeli_gosuchrezhdenij,_podvedomstvennyih_ministerstvu.doc";
            var res = Process(sourceFile);
            string output = DeclarationSerializer.Serialize(res);
            File.WriteAllText("output.json", output);
            Console.ReadKey();
        }

        private static IEnumerable<PublicServant> Process(string fileName)
        {
            string ext = Path.GetExtension(fileName);
            switch (ext)
            {
                case ".doc": string docXName = Doc2DocX(fileName); return ParseDocX(docXName, PropertyTypes);
                case ".docx": return ParseDocX(fileName, PropertyTypes);
                default: throw new Exception(@"Unsupported format in file {fileName}");
            }
        }

        private static string Doc2DocX(string fileName)
        {
            Application word = new Application();
            var doc = word.Documents.Open(Path.GetFullPath(fileName));
            string docXName = Path.GetFileNameWithoutExtension(fileName) + ".docx";
            string docXPath = Path.GetFullPath(docXName);
            doc.SaveAs2(docXPath, WdSaveFormat.wdFormatXMLDocument, CompatibilityMode: WdCompatibilityMode.wdWord2013);
            word.ActiveDocument.Close();
            word.Quit();

            return docXPath;
        }

        private static IEnumerable<PublicServant> ParseDocX(string fileName, Dictionary<String, RealEstateType> propertyTypes)
        {
            var parser = new DocXParser(PropertyTypes);
            return parser.Parse(fileName);
        }

    }
}
