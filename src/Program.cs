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
    class Program
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
            string declarationFile = string.Empty;
            int dumpColumn = -1;
            string outFile = "";
            string exportFile = "";
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

            IAdapter adapter = null;
            string extension = Path.GetExtension(declarationFile);
            string defaultOut = Path.GetFileNameWithoutExtension(declarationFile) + ".json";

            switch (extension)
            {
                case ".doc":
                case ".docx":
                    adapter = AsposeDocAdapter.CreateAdapter(declarationFile);
                    break;
                case ".xls":
                case ".xlsx":
                    adapter = AsposeExcelAdapter.CreateAdapter(declarationFile);
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

            if (columnOrdering == null)
            {
                columnOrdering = ColumnDetector.ExamineHeader(adapter);
            }
            adapter.ColumnOrdering = columnOrdering;

            Logger.SetLoggingLevel(verboseLevel);
            Logger.SetupLogFile(Path.GetFileName(declarationFile) + ".log");

            Logger.Info("Column ordering: ");
            foreach (var ordering in columnOrdering.ColumnOrder)
            {
                Logger.Info(ordering.ToString());
            }


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

            string output = DeclarationSerializer.Serialize(declaration, false);

            Logger.Info("Output size: " + output.Length);
            if (String.IsNullOrEmpty(outFile))
            {
                outFile = defaultOut;
            }
            Logger.Info("Writing json to " + outFile);
            File.WriteAllText(outFile, output);

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
