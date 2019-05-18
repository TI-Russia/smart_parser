<<<<<<< HEAD
﻿using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

using Microsoft.Office.Interop.Word;

using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;
using TI.Declarator.WordParser;

using CMDLine;

namespace Tindalos
{
    
    public class Tindalos
    {
        private static readonly string ErrorsFile = "errors.log";
        private static Dictionary<String, RealEstateType> PropertyTypes = new Dictionary<string, RealEstateType>();
        private static bool WriteJson = false;
        private static bool WriteHeader = false;
        private static string Action = "scan";
        private static bool Verbose = false;

        static Tindalos()
        {

        }
        static string ParseArgs (string[] args)
        {
            CMDLineParser parser = new CMDLineParser();
            CMDLineParser.Option actionOpt = parser.AddStringParameter("--action", "scan, test or full", true);
            CMDLineParser.Option writeJsonOpt = parser.AddBoolSwitch("--write-json", "write json");
            CMDLineParser.Option writeHeaderOpt = parser.AddBoolSwitch("--write-header", "write header");
            CMDLineParser.Option verboseOpt = parser.AddBoolSwitch("--verbose", "verbose");
            try
            {
                //parse the command line
                parser.Parse(args);
            }
            catch (Exception ex)
            {
                //show available options      
                Console.Write(parser.HelpMessage());
                Console.WriteLine();
                Console.WriteLine("Error: " + ex.Message);
                throw;
            }

            //replace argument list with remaining arguments
            WriteJson = writeJsonOpt.isMatched;
            WriteHeader = writeHeaderOpt.isMatched;
            Verbose = verboseOpt.isMatched;
            Action = actionOpt.Value.ToString();
            return String.Join(" ", parser.RemainingArgs()).Trim(new char[] { '"' });
        }

        static void Main(string[] args)
        {
            string inputFileName = ParseArgs(args);
            if (Action == "scan")
            {
                Scan(inputFileName);
            }
            else if (Action == "test")
            {
                Test(inputFileName);
            }
            else if (Action == "full") {
                Process(inputFileName);
            }
            else
            {
                Console.WriteLine("Error: unknown action" + Action);
            }

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

        static void Scan(string inputFileName)
        {
            if (Directory.Exists(inputFileName))
            {
                ScanDir(inputFileName);
            }
            else if (File.Exists(inputFileName))
            {
                ScanFile(inputFileName);
            }
            else
            {
                Console.WriteLine($"File or directory {inputFileName} not found.");
            }                     

            Console.WriteLine("Finished. Press any key.");
            Console.ReadKey();
        }

        public static Declaration Process(string fileName)
        {
            string ext = Path.GetExtension(fileName);
            switch (ext)
            {
                case ".html":
                case ".pdf":
                case ".doc": return ParseDocX(Doc2DocX(fileName));
                case ".docx": return ParseDocX(fileName);
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


        private static Declaration ParseDocX(string fileName)
        {
            var parser = new DocXParser();
            Declaration res = parser.Parse(fileName, Verbose);
            if (WriteJson)
            {
                string outputFile = Path.GetFileNameWithoutExtension(fileName) + ".json";
                File.WriteAllText(outputFile, DeclarationSerializer.Serialize(res));
            }

            return res;
        }

        private static void ScanDir(string dir)
        {
            Console.WriteLine($"Scanning directory {dir}");

            string dirName = new DirectoryInfo(dir).Name;
            string outputFile = dirName + ".txt";
            foreach (string fileName in Directory.GetFiles(dir))
            {
                ScanFile(fileName);
            }

            foreach (string subdir in Directory.GetDirectories(dir))
            {
                ScanDir(subdir);
            }
        }

        private static void ScanFile(string fileName)
        {
            Console.WriteLine($"Scanning file {fileName}");

            try
            { 
                string ext = Path.GetExtension(fileName);
                switch (ext)
                {
                    case ".html":
                    case ".pdf":
                    case ".doc":  ScanDocX(Doc2DocX(fileName)); break;
                    case ".docx": ScanDocX(fileName); break;
                    default: break;
                }
            }
            catch (Exception ex)
            {
                File.AppendAllLines(ErrorsFile, new string[] { fileName, ex.ToString() });
                Console.WriteLine($"There was an error scanning {fileName}. See {ErrorsFile} for details");
            }
        }

        private static void ScanDocX(string fileName)
        {
            var parser = new DocXParser();
            var co = parser.ScanProperties(fileName).ColumnOrdering;

            if (WriteHeader)
            {
                string outputFile = Path.GetFileNameWithoutExtension(fileName) + ".txt";
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
=======
﻿using System;
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

        }

        static void Main(string[] args)
        {
            //Scan(args);
            //Test(@"testfiles\2016_Sotrudniki_ministerstva.docx");
            //Test(@"testfiles\A - min_res_2011_Sotrudniki_ministerstva.doc");
            //Test(@"testfiles\C - min_health_2015_Sotrudniki_ministerstva.docx");
            Test(@"to_process\min_ind\2017_Rukovoditeli_ministerstva_(utochnionnye).docx");

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
                case ".doc": string docXName = Doc2DocX(fileName); return ParseDocX(docXName);
                case ".docx": return ParseDocX(fileName);
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

        private static Declaration ParseDocX(string fileName)
        {
            var parser = new DocXParser();
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
            var parser = new DocXParser();
            var co = parser.ScanProperties(fileName).ColumnOrdering;

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
>>>>>>> temp commit
