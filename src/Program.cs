using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;
using System.IO;
using Parser.Lib;
using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.ParserCommon;
using TI.Declarator.JsonSerialization;
using CMDLine;
using System.Security.Cryptography;
using DocumentFormat.OpenXml.Wordprocessing;
using Newtonsoft.Json;
using System.Reflection;
//using Newtonsoft.Json;

namespace Smart.Parser
    {
    public class SmartParserVersions
    {
        public List<Version> versions = new List<Version>();

        public class Version
        {
            public string id = "";
            public string info = "";
        }
    }

    public class Program
    {
        public static string OutFile = "";
        public static string AdapterFamily = "prod";
        static bool ColumnsOnly = false;

        static bool CheckJson = false;
        public static int MaxRowsToProcess = -1;
        public static DeclarationField ColumnToDump = DeclarationField.None;
        public static string TolokaFileName = "";
        public static string HtmlFileName = "";
        public static bool SkipRelativeOrphan = false;
        public static bool ValidateByApi = false;
        public static bool IgnoreDirectoryIds = false;
        public static bool BuildTrigrams = false;
        public static int? UserDocumentFileId;

        static string ParseArgs(string[] args)
        {
            CMDLineParser parser = new CMDLineParser();
            CMDLineParser.Option outputOpt = parser.AddStringParameter("-o", "use file for output", false);
            CMDLineParser.Option licenseOpt = parser.AddStringParameter("-license", "", false);
            CMDLineParser.Option mainLogOpt = parser.AddStringParameter("-log", "", false);
            CMDLineParser.Option skipLoggingOpt = parser.AddBoolSwitch("-skip-logging", "");
            CMDLineParser.Option verboseOpt =
                parser.AddStringParameter("-v", "verbose level: debug, info, error", false);
            CMDLineParser.Option columnsOnlyOpt = parser.AddBoolSwitch("-columnsonly", "");
            CMDLineParser.Option checkJsonOpt = parser.AddBoolSwitch("-checkjson", "");
            CMDLineParser.Option adapterOpt = parser.AddStringParameter("-adapter",
                "can be aspose,npoi, microsoft or prod, by default is aspose", false);
            CMDLineParser.Option maxRowsToProcessOpt =
                parser.AddStringParameter("-max-rows", "max rows to process from the input file", false);
            CMDLineParser.Option dumpColumnOpt = parser.AddStringParameter("-dump-column",
                "dump column identified by enum DeclarationField and exit", false);
            CMDLineParser.Option dumpHtmlOpt = parser.AddStringParameter("-dump-html", "dump table to html", false);
            CMDLineParser.Option tolokaFileNameOpt =
                parser.AddStringParameter("-toloka", "generate toloka html", false);
            CMDLineParser.Option skipRelativeOrphanOpt = parser.AddBoolSwitch("-skip-relative-orphan", "");
            CMDLineParser.Option apiValidationOpt =
                parser.AddBoolSwitch("-api-validation", "validate JSON output by API call");
            CMDLineParser.Option buildTrigramsOpt = parser.AddBoolSwitch("-build-trigrams", "build trigrams");
            CMDLineParser.Option checkPredictorOpt =
                parser.AddBoolSwitch("-check-predictor", "calc predictor precision");
            CMDLineParser.Option docFileIdOpt = parser.AddStringParameter("-docfile-id",
                "document id to initialize document/documentfile_id", false);
            CMDLineParser.Option convertedFileStorageUrlOpt = parser.AddStringParameter("-converted-storage-url",
                "document id to initialize document/documentfile_id for example http://c.disclosures.ru:8091, the default value is read from env variable DECLARATOR_CONV_URL",
                false);
            CMDLineParser.Option fioOnlyOpt = parser.AddBoolSwitch("-fio-only", "");
            CMDLineParser.Option useDecimalRawNormalizationOpt = parser.AddBoolSwitch("-decimal-raw-normalization",
                "print raw floats in Russian traditional format");
            CMDLineParser.Option disclosuresOpt = parser.AddBoolSwitch("-disclosures",
                "use disclosures output format: save sheet id to each each section, do not produce many output files but one");
            CMDLineParser.Option versionOpt = parser.AddBoolSwitch("-version",
                "print version");
            parser.AddHelpOption();
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

            if (versionOpt.isMatched)
            {
                PrintVersion();
                System.Environment.Exit(0);
            }
            if (licenseOpt.isMatched)
            {
                AsposeLicense.SetLicense(licenseOpt.Value.ToString());
                if (!AsposeLicense.Licensed)
                {
                    throw new SmartParserException("Not valid aspose licence " + licenseOpt.Value.ToString());
                }
            }

            Smart.Parser.Lib.Parser.InitializeSmartParser();
            if (maxRowsToProcessOpt.isMatched)
            {
                MaxRowsToProcess = System.Convert.ToInt32(maxRowsToProcessOpt.Value.ToString());
            }

            if (docFileIdOpt.isMatched)
            {
                UserDocumentFileId = System.Convert.ToInt32(docFileIdOpt.Value.ToString());
            }
            if (disclosuresOpt.isMatched)
            {
                DeclarationSerializer.SmartParserJsonFormat = SmartParserJsonFormatEnum.Disclosures;
            }

            string logFileName = "";
            if (mainLogOpt.isMatched)
            {
                logFileName = Path.GetFullPath(mainLogOpt.Value.ToString());
            }

            Logger.Setup(logFileName, skipLoggingOpt.isMatched);
            if (outputOpt.isMatched)
            {
                OutFile = outputOpt.Value.ToString();
            }

            Logger.LogLevel verboseLevel = Logger.LogLevel.Info;
            if (verboseOpt.isMatched)
            {
                switch (verboseOpt.Value.ToString())
                {
                    case "info":
                        verboseLevel = Logger.LogLevel.Info;
                        break;
                    case "error":
                        verboseLevel = Logger.LogLevel.Error;
                        break;
                    case "debug":
                        verboseLevel = Logger.LogLevel.Debug;
                        break;
                    default:
                        {
                            throw new Exception("unknown verbose level " + verboseOpt.Value.ToString());
                        }
                }
            }

            Logger.SetLoggingLevel(verboseLevel);

            SkipRelativeOrphan = skipRelativeOrphanOpt.isMatched;
            ValidateByApi = apiValidationOpt.isMatched;

            if (adapterOpt.isMatched)
            {
                AdapterFamily = adapterOpt.Value.ToString();
                if (AdapterFamily != "aspose" &&
                    AdapterFamily != "npoi" &&
                    AdapterFamily != "microsoft" &&
                    AdapterFamily != "prod")
                {
                    throw new Exception("unknown adapter family " + AdapterFamily);
                }
            }

            if (dumpColumnOpt.isMatched)
            {
                ColumnToDump = (DeclarationField)Enum.Parse(typeof(DeclarationField), dumpColumnOpt.Value.ToString());
            }

            if (dumpHtmlOpt.isMatched)
            {
                HtmlFileName = dumpHtmlOpt.Value.ToString();
            }

            if (convertedFileStorageUrlOpt.isMatched)
            {
                IAdapter.ConvertedFileStorageUrl = convertedFileStorageUrlOpt.Value.ToString();
            }

            if (tolokaFileNameOpt.isMatched)
            {
                TolokaFileName = tolokaFileNameOpt.Value.ToString();
            }

            if (useDecimalRawNormalizationOpt.isMatched)
            {
                Smart.Parser.Lib.Parser.UseDecimalRawNormalization = true;
            }


            ColumnsOnly = columnsOnlyOpt.isMatched;
            ColumnOrdering.SearchForFioColumnOnly = fioOnlyOpt.isMatched;
            CheckJson = checkJsonOpt.isMatched;
            BuildTrigrams = buildTrigramsOpt.isMatched;
            ColumnPredictor.CalcPrecision = checkPredictorOpt.isMatched;
            var freeArgs = parser.RemainingArgs();
            return String.Join(" ", freeArgs).Trim(new char[] { '"' });
        }

        public static void PrintVersion()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Resources.versions.txt"))
            {
                using (var file = new System.IO.StreamReader(stream))
                {
                    string jsonStr = file.ReadToEnd();
                    var versions = JsonConvert.DeserializeObject<SmartParserVersions>(jsonStr);
                    Console.WriteLine(versions.versions[versions.versions.Count - 1].id);
                }
            }
        }

        public static string BuildOutFileNameByInput(string inputFile)
        {
            return Path.Combine(Path.GetDirectoryName(inputFile), Path.GetFileName(inputFile) + ".json");
        }

        static bool IsDirectory(string fileName)
        {
            try
            {
                return (File.GetAttributes(fileName) & FileAttributes.Directory) == FileAttributes.Directory;
            }
            catch
            {
                return false;
            }
        }



        private static string SupportedFileTypesPattern = "*.pdf, *.xls, *.xlsx, *.doc, *.docx, *.html";

        public static int ParseDirectory(string dirName)
        {
            string[] files = Directory.GetFiles(dirName, SupportedFileTypesPattern);
            return ParseMultipleFiles(Directory.GetFiles(dirName), dirName);
        }

        public static int ParseByFileMask(string fileMask)
        {
            string[] files = null;
            if (fileMask.StartsWith("@"))
            {
                string fileName = fileMask.Substring(1);
                Logger.Info("Reading files list from " + fileName);

                files = File.ReadAllLines(fileName).ToArray();
            }
            else
            {
                Logger.Info("Parsing files by mask " + fileMask);

                files = Directory.GetFiles(Path.GetDirectoryName(fileMask), Path.GetFileName(fileMask),
                    SearchOption.AllDirectories);
            }

            Logger.Info("Found {0} files", files.Count());

            return ParseMultipleFiles(files, Path.GetDirectoryName(fileMask));
        }

        public static int ParseMultipleFiles(IEnumerable<string> files, string outputDir)
        {
            var parse_results = new Dictionary<string, List<string>>
            {
                {"ok", new List<string>()},
                {"error", new List<string>()},
                {"too_many_errors", new List<string>()},
                {"exception", new List<string>()},
            };

            foreach (string file in files)
            {
                Logger.Info("Parsing file " + file);
                bool caught = false;
                try
                {
                    Logger.SetOutSecond();
                    ParseFile(file, BuildOutFileNameByInput(file));
                }
                catch (SmartParserException e)
                {
                    caught = true;
                    Logger.Error("Parsing Exception " + e.ToString());
                    parse_results["exception"].Add(file);
                }
                catch (Exception e)
                {
                    caught = true;
                    Logger.Error("Parsing Exception " + e.ToString());
                    Logger.Debug("Stack: " + e.StackTrace);
                    parse_results["exception"].Add(file);
                }
                finally
                {
                    Logger.SetOutMain();
                }

                if (caught)
                {
                    Logger.Info("Result: Exception");
                }

                if (!caught && Logger.Errors.Any())
                {
                    Logger.Info("Result: error");
                    parse_results["error"].Add(file);
                }

                if (!caught && !Logger.Errors.Any())
                {
                    Logger.Info("Result: OK");
                    parse_results["ok"].Add(file);
                }

                if (Logger.Errors.Any())
                {
                    Logger.Info(" Parsing errors ({0})", Logger.Errors.Count());

                    foreach (string e in Logger.Errors)
                    {
                        Logger.Info(e);
                    }
                }
            }

            Logger.Info("Parsing Results:");

            foreach (var key_value in parse_results)
            {
                Logger.Info("Result: {0} ({1})", key_value.Key, key_value.Value.Count());
                foreach (string file in key_value.Value)
                {
                    Logger.Info(file);
                }
            }

            if (Logger.UnknownRealEstate.Count() > 0)
            {
                Logger.Info("UnknownRealEstate.Count: {0}", Logger.UnknownRealEstate.Count());
                string content = string.Join("\n", Logger.UnknownRealEstate);
                string dictfile = Path.Combine(outputDir, "UnknownRealEstate.txt");
                File.WriteAllText(dictfile, content);
                Logger.Info("Output UnknownRealEstate to file {0}", dictfile);
            }

            if (ColumnPredictor.CalcPrecision)
            {
                Logger.Info(ColumnPredictor.GetPrecisionStr());
            }

            return 0;
        }

        static IAdapter GetAdapter(string inputFile)
        {
            string extension = Path.GetExtension(inputFile).ToLower();
            switch (extension)
            {
                case ".htm":
                case ".html":
                    if (HtmAdapter.CanProcess(inputFile))
                    {
                        return new HtmAdapter(inputFile);
                    }
                    else
                    {
                        return new AngleHtmlAdapter(inputFile, MaxRowsToProcess);
                    }
                case ".pdf":
                case ".xhtml":
                case ".doc":
                case ".rtf":
                case ".toloka_json":
                case ".docx":
                    return OpenXmlWordAdapter.CreateAdapter(inputFile, MaxRowsToProcess);
                case ".xls":
                case ".xlsx":
                    if (AdapterFamily == "aspose" || AdapterFamily == "prod")
                    {
                        if (!AsposeLicense.Licensed && extension == ".xls")
                        {
                            throw new Exception("xls file format is not supported");
                        }

                        if (AsposeLicense.Licensed)
                        {
                            return AsposeExcelAdapter.CreateAdapter(inputFile, MaxRowsToProcess);
                        }
                    }
                    else if (AdapterFamily == "npoi")
                    {
                        return NpoiExcelAdapter.CreateAdapter(inputFile, MaxRowsToProcess);
                    }
                    else
                    {
                        return null;
                    }

                    break;
                default:
                    Logger.Error("Unknown file extension " + extension);
                    return null;
            }

            Logger.Error("Cannot find adapter for " + inputFile);
            return null;
        }

        static void DumpColumn(IAdapter adapter, ColumnOrdering columnOrdering, DeclarationField columnToDump)
        {
            int rowOffset = columnOrdering.FirstDataRow;
            for (var row = rowOffset; row < adapter.GetRowsCount(); row++)
            {
                DataRow currRow = adapter.GetRow(columnOrdering, row);
                var cell = currRow.GetDeclarationField(columnToDump);
                var s = (cell == null) ? "null" : cell.GetText();
                s = s.Replace("\n", "\\n");
                Console.WriteLine(s);
            }
        }

        public static string CalculateMD5(string filename)
        {
            using (var md5 = MD5.Create())
            {
                using (var stream = File.OpenRead(filename))
                {
                    var hash = md5.ComputeHash(stream);
                    return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
                }
            }
        }

        static string BuildInputFileId(IAdapter adapter, string filename)
        {
            return CalculateMD5(filename) + "_" + adapter.GetWorksheetName();
        }

        public static void SaveRandomPortionToToloka(IAdapter adapter, ColumnOrdering columnOrdering,
            Declaration declaration, string inputFileName)
        {
            if (TolokaFileName == "") return;
            string fileID = BuildInputFileId(adapter, inputFileName);
            using (System.IO.StreamWriter file = new System.IO.StreamWriter(TolokaFileName))
            {
                file.WriteLine("INPUT:input_id\tINPUT:input_json\tGOLDEN:declaration_json\tHINT:text");
                Random random = new Random();
                int dataRowsCount = Math.Min(20, adapter.GetRowsCount() - columnOrdering.GetPossibleHeaderEnd());
                int dataStart = random.Next(columnOrdering.GetPossibleHeaderEnd(),
                    adapter.GetRowsCount() - dataRowsCount);
                int dataEnd = dataStart + dataRowsCount;
                var json = adapter.TablePortionToJson(columnOrdering, dataStart, dataEnd);
                json.InputFileName = inputFileName;
                json.Title = declaration.Properties.SheetTitle;
                string jsonStr = JsonConvert.SerializeObject(json);
                jsonStr = jsonStr.Replace("\t", " ").Replace("\\t", " ").Replace("\"", "\"\"");
                string id = fileID + "_" + dataStart + "_" + dataEnd;
                file.WriteLine(id + "\t" + "\"" + jsonStr + "\"\t\t");
            }
        }

        static Declaration BuildDeclarations(IAdapter adapter, string inputFile)
        {
            Declaration declaration;
            string inputFileName = Path.GetFileName(inputFile);
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter, !SkipRelativeOrphan);

            if (adapter.CurrentScheme == default)
            {
                var columnOrdering = ColumnDetector.ExamineTableBeginning(adapter);

                // Try to extract declaration year from file name if we weren't able to get it from document title
                if (!columnOrdering.Year.HasValue)
                {
                    columnOrdering.Year = TextHelpers.ExtractYear(inputFileName);
                }

                Logger.Info("Column ordering: ");
                foreach (var ordering in columnOrdering.ColumnOrder)
                {
                    Logger.Info(ordering.ToString());
                }

                Logger.Info(String.Format("OwnershipTypeInSeparateField: {0}",
                    columnOrdering.OwnershipTypeInSeparateField));

                if (ColumnsOnly)
                    return null;

                if (ColumnToDump != DeclarationField.None)
                {
                    DumpColumn(adapter, columnOrdering, ColumnToDump);
                    return null;
                }

                if (columnOrdering.Title != null)
                {
                    Logger.Info("Declaration Title: {0} ", columnOrdering.Title);
                }

                if (columnOrdering.Year != null)
                {
                    Logger.Info("Declaration Year: {0} ", columnOrdering.Year.Value);
                }

                if (columnOrdering.MinistryName != null)
                {
                    Logger.Info("Declaration Ministry: {0} ", columnOrdering.MinistryName);
                }


                if (!(columnOrdering.ContainsField(DeclarationField.NameOrRelativeType) ||
                      columnOrdering.ContainsField(DeclarationField.NameAndOccupationOrRelativeType)))
                {
                    // TODO сначала поискать первый section_row и проверить, именно там может быть ФИО
                    // https://declarator.org/admin/declarations/jsonfile/186842/change/
                    throw new SmartParserException("Insufficient fields: No any of Declarant Name fields found.");
                }

                if (!(columnOrdering.ContainsField(DeclarationField.DeclarantIncome) ||
                      columnOrdering.ContainsField(DeclarationField.DeclarantIncomeInThousands) ||
                      columnOrdering.ContainsField(DeclarationField.DeclaredYearlyIncome) ||
                      columnOrdering.ContainsField(DeclarationField.DeclaredYearlyIncomeThousands)))
                {
                    if (!ColumnOrdering.SearchForFioColumnOnly)
                    {
                        throw new SmartParserException("Insufficient fields: No any of Declarant Income fields found.");
                    }
                }

                declaration = parser.Parse(columnOrdering, BuildTrigrams, UserDocumentFileId);
                SaveRandomPortionToToloka(adapter, columnOrdering, declaration, inputFile);
            }
            else
            {
                declaration = adapter.CurrentScheme.Parse(parser, UserDocumentFileId);
            }
            return declaration;
        }

        static string DumpDeclarationsToJson(string inputFile, Declaration declaration)
        {
            string schema_errors = null;
            string output = DeclarationSerializer.Serialize(declaration, ref schema_errors);

            if (!String.IsNullOrEmpty(schema_errors))
            {
                Logger.Error("Json schema errors:" + schema_errors);
            }
            else
            {
                Logger.Info("Json schema OK");
            }

            Logger.Info("Output size: " + output.Length);

            if (ValidateByApi)
            {
                string validationResult = ApiClient.ValidateParserOutput(output);
                if (validationResult != "[]")
                {
                    string inputFileName = Path.GetFileName(inputFile);
                    string errorsFileName = "validation_errors_" +
                                            Path.GetFileNameWithoutExtension(inputFileName) + ".json";
                    var rep = MiscSerializer.DeserializeValidationReport(validationResult);
                    File.WriteAllText(errorsFileName, validationResult);
                    Logger.Error("Api validation failed. Errors:" + errorsFileName);
                }
            }
            return output;
        }

        public static void WriteOutputJson (string inputFile, Declaration declarations, string outFile)
        {
            if (declarations != null)
            {
                string output = DumpDeclarationsToJson(inputFile, declarations);
                Logger.Info("Writing json to " + outFile);
                File.WriteAllBytes(outFile, Encoding.UTF8.GetBytes(output));
            }
        }

        public static int ParseFile(string inputFile, string outFile)
        {
            if (CheckJson && File.Exists(outFile))
            {
                Logger.Info("JSON file {0} already exist", outFile);
                return 0;
            }

            if (!File.Exists(inputFile))
            {
                Logger.Info("ERROR: {0} file NOT exists", inputFile);
                return 0;
            }


            ColumnPredictor.InitializeIfNotAlready();

            string logFile = Path.Combine(Path.GetDirectoryName(inputFile),
                Path.GetFileName(inputFile) + ".log");
            Logger.SetSecondLogFileName(Path.GetFullPath(logFile));

            Logger.Info(String.Format("Parsing {0}", inputFile));
            IAdapter adapter = GetAdapter(inputFile);

            Logger.Info(String.Format("TablesCount = {0}", adapter.GetTablesCount()));
            Logger.Info(String.Format("RowsCount = {0}", adapter.GetRowsCount()));

            if (adapter.GetTablesCount() == 0 && !inputFile.EndsWith(".toloka_json"))
                throw new SmartParserException("No tables found in document");

            if (HtmlFileName != "")
                adapter.WriteHtmlFile(HtmlFileName);

            if (adapter.GetWorkSheetCount() > 1)
            {
                Logger.Info(String.Format("File has multiple ({0}) worksheets", adapter.GetWorkSheetCount()));
                Declaration allDeclarations = null;
                for (int sheetIndex = 0; sheetIndex < adapter.GetWorkSheetCount(); sheetIndex++)
                {
                    adapter.SetCurrentWorksheet(sheetIndex);
                    try
                    {
                        if (DeclarationSerializer.SmartParserJsonFormat == SmartParserJsonFormatEnum.Disclosures)
                        {
                            var sheetDeclarations = BuildDeclarations(adapter, inputFile);
                            if (allDeclarations == null)
                            {
                                allDeclarations = sheetDeclarations;
                            }
                            else
                            {
                                allDeclarations.AddDeclarations(sheetDeclarations);
                            }
                        }
                        else
                        {
                            string curOutFile = outFile.Replace(".json", "_" + sheetIndex.ToString() + ".json");
                            Logger.Info(String.Format("Parsing worksheet {0} into file {1}", sheetIndex, curOutFile));
                            WriteOutputJson(inputFile, BuildDeclarations(adapter, inputFile), curOutFile);

                        }
                    }
                    catch (ColumnDetectorException)
                    {
                        Logger.Info(String.Format("Skipping empty sheet {0} (No headers found exception thrown)",
                            sheetIndex));
                    }
                    if (allDeclarations != null)
                    {
                        WriteOutputJson(inputFile, allDeclarations, outFile);
                    }
                }
            }
            else
            {
                WriteOutputJson(inputFile, BuildDeclarations(adapter, inputFile), outFile);
            }

            return 0;
        }
        public static int Main(string[] args)
        {
            string inputFile = ParseArgs(args);
            Logger.Info("Command line: " + String.Join(" ", args));
            if (String.IsNullOrEmpty(inputFile))
            {
                Console.WriteLine("no input file or directory");
                return 1;
            }


            if (IsDirectory(inputFile))
            {
                return ParseDirectory(inputFile);
            }

            if (inputFile.Contains("*") || inputFile.Contains("?") || inputFile.StartsWith("@"))
            {
                return ParseByFileMask(inputFile);
            }

            try
            {
                Logger.SetOutSecond();
                if (OutFile == "")
                {
                    OutFile = BuildOutFileNameByInput(inputFile);
                }

                ParseFile(inputFile, OutFile);
            }
            catch (SmartParserException e)
            {
                Logger.Error("Parsing Exception " + e.ToString());
            }
            catch (Exception e)
            {
                Logger.Error("Unknown Parsing Exception " + e.ToString());
                Logger.Info("Stack: " + e.StackTrace);
            }
            finally
            {
                Logger.SetOutMain();
            }

            if (ColumnPredictor.CalcPrecision)
            {
                Logger.Info(ColumnPredictor.GetPrecisionStr());
            }

            if (Logger.Errors.Count() > 0)
            {
                Logger.Info("*** Errors ({0}):", Logger.Errors.Count());

                foreach (string e in Logger.Errors)
                {
                    Logger.Info(e);
                }
            }

            return 0;
        }

    }

}
