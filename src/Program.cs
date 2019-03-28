using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;
using System.Reflection;
using System.IO;
using Parser.Lib;
using TI.Declarator.ParserCommon;
using TI.Declarator.JsonSerialization;

namespace Smart.Parser
{
    public class Program
    {
        static void ShowHelp()
        {
            Console.WriteLine("Usage: {0}.exe [options] [declaration file]", typeof(Program).Assembly.GetName().Name);
            Console.WriteLine("Options:");
            Console.WriteLine("    -d column             - dump column content.");
            Console.WriteLine("    -h                    - show this help.");
            Console.WriteLine("    -o file               - use file for output");
        }
        /**
         * Command line parameters
         * 
         * 
         */
        public static int Main(string[] args)
        {
            DeclaratorApiPatterns patterns;
            string declarationFile = string.Empty;
            int dumpColumn = -1;
            string outFile = "";
            string exportFile = "";
            string logFile = "";
            ColumnOrdering columnOrdering = null;
            string verbose = "";
            Logger.LogLevel verboseLevel = Logger.LogLevel.Error;

            Logger.Setup();
            Logger.Info("Command line: " + String.Join(" ", args));

            for (int i = 0; i < args.Length; ++i)
            {
                if (args[i].StartsWith("-"))
                {
                    switch (args[i])
                    {
                        case "-h":
                        case "/h":
                        case "--help":
                        case "/?":
                            ShowHelp();
                            return 1;

                        case "-d":
                            if (i + 1 < args.Length)
                                dumpColumn = Convert.ToInt32(args[++i]);
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;

                        case "-ordering":
                            if (i + 1 < args.Length)
                                columnOrdering = JsonWriter.ReadJson<ColumnOrdering>(args[++i]);
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;

                        case "-license":
                            if (i + 1 < args.Length)
                                AsposeLicense.SetLicense(args[++i]);
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;

                        case "-export":
                            if (i + 1 < args.Length)
                                exportFile = args[++i];
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;

                        case "-log":
                            if (i + 1 < args.Length)
                                logFile = args[++i];
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;



                        case "-o":
                            if (i + 1 < args.Length)
                                outFile = args[++i];
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;

                        case "-v":
                            if (i + 1 < args.Length)
                            {
                                verbose = args[++i];
                                switch (verbose)
                                {
                                    case "info": verboseLevel = Logger.LogLevel.Info; break;
                                    case "error": verboseLevel = Logger.LogLevel.Error; break;
                                    case "debug": verboseLevel = Logger.LogLevel.Debug; break;
                                    default:
                                        {
                                            ShowHelp();
                                            return 1;
                                        }
                                }
                            }
                            else
                            {
                                ShowHelp();
                                return 1;
                            }
                            break;


                        case "-q":
                            break;

                        default:
                            {
                                Console.WriteLine("Invalid option " + args[i]);
                                return 1;
                            }
                    }
                    continue;
                }
                if (declarationFile == string.Empty)
                    declarationFile = args[i];
                else
                {
                    ShowHelp();
                    return 1;
                }

            }

            if (String.IsNullOrEmpty(declarationFile))
            {
                ShowHelp();
                return 1;
            }

            if (declarationFile.Contains("*") || declarationFile.Contains("?"))
            {
                return ParseMultipleFiles(declarationFile);
            }


            try
            {
                Logger.SetOutSecond();
                ParseOneFile(declarationFile);
            }
            catch (SmartParserException e)
            {
                Logger.Info("Parsing Exception " + e.ToString());
            }
            catch (Exception e)
            {
                Logger.Info("Parsing Exception " + e.ToString());
                Logger.Info("Stack: " + e.StackTrace);
            }
            finally
            {
                Logger.SetOutMain();
            }

            /*
                        IAdapter adapter = null;
                        string extension = Path.GetExtension(declarationFile);
                        string defaultOut = Path.GetFileNameWithoutExtension(declarationFile) + ".json";

                        switch (extension)
                        {
                            case ".doc":
                            case ".docx":
                                if (!AsposeLicense.Licensed)
                                {
                                    throw new Exception("doc and docx file format is not supported");
                                }
                                adapter = AsposeDocAdapter.CreateAdapter(declarationFile);
                                break;
                            case ".xls":
                            case ".xlsx":
                                if (!AsposeLicense.Licensed && extension == ".xls")
                                {
                                    throw new Exception("xls file format is not supported");
                                }
                                if (AsposeLicense.Licensed)
                                { 
                                    adapter = AsposeExcelAdapter.CreateAdapter(declarationFile);
                                }
                                else
                                { 
                                    adapter = TI.Declarator.ExcelParser.XlsxParser.GetAdapter(declarationFile);
                                }
                                break;
                            default:
                                Logger.Error("Unknown file extension " + extension);
                                return 1;
                        }

                        Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);

                        if (dumpColumn >= 0)
                        {
                            parser.DumpColumn(dumpColumn);
                            return 0;
                        }

                        if (exportFile != "")
                        {
                            parser.ExportCSV(exportFile);
                            return 0;
                        }


                        if (logFile == "")
                        {
                            logFile = Path.GetFileName(declarationFile) + ".log";
                        }

                        Logger.SetLoggingLevel(verboseLevel);
                        Logger.SetSecondLogFileName(logFile);

                        if (columnOrdering == null)
                        {
                            columnOrdering = ColumnDetector.ExamineHeader(adapter);
                        }
                        adapter.ColumnOrdering = columnOrdering;


                        Logger.Info("Column ordering: ");
                        foreach (var ordering in columnOrdering.ColumnOrder)
                        {
                            Logger.Info(ordering.ToString());
                        }
                        Logger.Info(String.Format("OwnershipTypeInSeparateField: {0}", columnOrdering.OwnershipTypeInSeparateField));


                        Logger.Info(String.Format("Parsing {0} Rows {1}", declarationFile, adapter.GetRowsCount()));

                        Declaration declaration = null;
                        try
                        {
                            declaration = parser.Parse();
                        }
                        catch(Exception e)
                        {
                            Logger.Info("Parsing error " + e.ToString());
                            return 1;
                        }

                        string output = "";
                        try
                        {
                            output = DeclarationSerializer.Serialize(declaration, false);
                        }
                        catch (Exception e)
                        {
                            Logger.Info("Serialization error " + e.ToString());
                            return 1;
                        }

                        Logger.Info("Output size: " + output.Length);
                        if (String.IsNullOrEmpty(outFile))
                        {
                            outFile = defaultOut;
                        }
                        Logger.Info("Writing json to " + outFile);
                        File.WriteAllText(outFile, output);
            */
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

        public static int ParseMultipleFiles(string fileMask)
        {
            Logger.Info("Parsing files by mask " + fileMask);

            string[] files = Directory.GetFiles(Path.GetDirectoryName(fileMask), Path.GetFileName(fileMask),
                SearchOption.AllDirectories);

            Logger.Info("Found {0} files", files.Count());

            var parse_results = new Dictionary<string, List<string>>
            {
                { "ok", new List<string>() },
                { "error", new List<string>() },
                { "too_many_errors", new List<string>() },
                { "exception", new List<string>() },
            };

            foreach (string file in files)
            {
                Logger.Info("Parsing file " + file);
                bool caught = false;
                try
                {
                    Logger.SetOutSecond();
                    ParseOneFile(file);
                }
                catch (SmartParserException e)
                {
                    caught = true;
                    Logger.Info("Parsing Exception " + e.ToString());
                    parse_results["too_many_errors"].Add(file);
                }
                catch (Exception e)
                {
                    caught = true;
                    Logger.Info("Parsing Exception " + e.ToString());
                    Logger.Info("Stack: " + e.StackTrace);
                    parse_results["exception"].Add(file);
                }
                finally
                {
                    Logger.SetOutMain();
                }
                if (!caught && Logger.Errors.Count() > 0)
                {
                    parse_results["error"].Add(file);
                }
                if (!caught && Logger.Errors.Count() == 0)
                {
                    parse_results["ok"].Add(file);
                }

                if (Logger.Errors.Count() > 0)
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
                string dictfile = Path.Combine(Path.GetDirectoryName(fileMask), "UnknownRealEstate.txt");
                File.WriteAllText(dictfile, content);
                Logger.Info("Output UnknownRealEstate to file {0}", dictfile);
            }

            return 0;
        }



        public static int ParseOneFile(string declarationFile)
        {
            IAdapter adapter = null;
            string extension = Path.GetExtension(declarationFile);
            string outFile = Path.Combine(Path.GetDirectoryName(declarationFile), Path.GetFileNameWithoutExtension(declarationFile) + ".json");
            string logFile = Path.Combine(Path.GetDirectoryName(declarationFile), Path.GetFileName(declarationFile) + ".log");
            Logger.SetSecondLogFileName(logFile);


            switch (extension)
            {
                case ".doc":
                case ".docx":
                    if (!AsposeLicense.Licensed)
                    {
                        throw new Exception("doc and docx file format is not supported");
                    }
                    adapter = AsposeDocAdapter.CreateAdapter(declarationFile);
                    break;
                case ".xls":
                case ".xlsx":
                    if (!AsposeLicense.Licensed && extension == ".xls")
                    {
                        throw new Exception("xls file format is not supported");
                    }
                    if (AsposeLicense.Licensed)
                    {
                        adapter = AsposeExcelAdapter.CreateAdapter(declarationFile);
                    }
                    else
                    {
                        adapter = TI.Declarator.ExcelParser.XlsxParser.GetAdapter(declarationFile);
                    }
                    break;
                default:
                    Logger.Error("Unknown file extension " + extension);
                    return 1;
            }

            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);

            var columnOrdering = ColumnDetector.ExamineHeader(adapter);

            adapter.ColumnOrdering = columnOrdering;


            Logger.Info("Column ordering: ");
            foreach (var ordering in columnOrdering.ColumnOrder)
            {
                Logger.Info(ordering.ToString());
            }
            Logger.Info(String.Format("OwnershipTypeInSeparateField: {0}", columnOrdering.OwnershipTypeInSeparateField));
            Logger.Info(String.Format("Parsing {0} Rows {1}", declarationFile, adapter.GetRowsCount()));

            Declaration declaration = parser.Parse();

            string output = DeclarationSerializer.Serialize(declaration, false/*true*/);

            Logger.Info("Output size: " + output.Length);

            Logger.Info("Writing json to " + outFile);
            File.WriteAllText(outFile, output);

            return 0;

        }

    }

}
