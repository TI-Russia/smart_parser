using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

using Microsoft.Office.Interop.Word;

using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;
using TI.Declarator.WordParser;

namespace Tindalos
{
    public class Tindalos
    {
        private static readonly string ErrorsFile = "errors.log";
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
            //Scan(args);
            //Test(@"regression\2016_Sotrudniki_ministerstva.docx");
            Test(@"testfiles\A - min_res_2011_Sotrudniki_ministerstva.doc");
            //Test(@"testfiles\C - min_health_2015_Sotrudniki_ministerstva.docx");

            //var ue = new UnknownEntry
            //{
            //    Contents = "квортира",
            //    EntryType = "realestatetype",
            //    FileName = "imaginary_file.docx",
            //    DocumentFileId = "1337",
            //    WordPageNumber = 3
            //};

            //ApiClient.ReportUnknownEntry(ue);

            Console.WriteLine("Press any key..");
            Console.ReadKey();
        }

    
        static string Test(string filename)
        {            
            Declaration res = Process(filename);
            string output = DeclarationSerializer.Serialize(res);

            string validationResult = ApiClient.ValidateParserOutput(output);
            string errorsFileName = "errors_" + Path.GetFileNameWithoutExtension(filename) + ".json";

            var rep = MiscSerializer.DeserializeValidationReport(validationResult);
            File.WriteAllText(errorsFileName, validationResult);

            string outputFileName = Path.GetFileNameWithoutExtension(filename) + ".json";
            File.WriteAllText(outputFileName, output);

            return outputFileName;            
        }

        static void Scan(string[] args)
        {
            string arg = String.Join(" ", args).Trim(new char[] { '"' });
            if (Directory.Exists(arg))
            {
                ScanDir(arg);
            }
            else if (File.Exists(arg))
            {
                string outputFile = Path.GetFileNameWithoutExtension(arg) + ".txt";
                ScanFile(arg, outputFile);
            }
            else
            {
                Console.WriteLine($"File or directory {arg} not found.");
            }                     

            Console.WriteLine("Finished. Press any key.");
            Console.ReadKey();
        }

        public static Declaration Process(string fileName)
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

        private static Declaration ParseDocX(string fileName, Dictionary<String, RealEstateType> propertyTypes)
        {
            var parser = new DocXParser(PropertyTypes);
            return parser.Parse(fileName);
        }

        private static void ScanDir(string dir)
        {
            Console.WriteLine($"Scanning directory {dir}");

            string dirName = new DirectoryInfo(dir).Name;
            string outputFile = dirName + ".txt";
            foreach (string fileName in Directory.GetFiles(dir))
            {
                ScanFile(fileName, outputFile);
            }

            foreach (string subdir in Directory.GetDirectories(dir))
            {
                ScanDir(subdir);
            }
        }

        private static void ScanFile(string fileName, string outputFile = null)
        {
            Console.WriteLine($"Scanning file {fileName}");

            try
            { 
                string ext = Path.GetExtension(fileName);
                switch (ext)
                {
                    case ".doc": string docXName = Doc2DocX(fileName); ScanDocX(docXName, outputFile); break;
                    case ".docx": ScanDocX(fileName, outputFile); break;
                    default: break;
                }
            }
            catch (Exception ex)
            {
                File.AppendAllLines(ErrorsFile, new string[] { fileName, ex.ToString() });
                Console.WriteLine($"There was an error scanning {fileName}. See {ErrorsFile} for details");
            }
        }

        private static void ScanDocX(string fileName, string outputFile = null)
        {
            var parser = new DocXParser(null);
            var co = parser.Scan(fileName).ColumnOrdering;

            if (outputFile != null)
            {
                var outBuilder = new StringBuilder();
                outBuilder.AppendLine(fileName);
                foreach (var fieldObj in Enum.GetValues(typeof(DeclarationField)))
                {

                    var field = (DeclarationField)fieldObj;
                    var colNumber = co[field];
                    if (colNumber.HasValue)
                    {
                        outBuilder.Append($"{field} {colNumber}|");
                    }
                }
                outBuilder.AppendLine();
                outBuilder.AppendLine();

                File.AppendAllText(outputFile, outBuilder.ToString());
            }
        }

    }
}
