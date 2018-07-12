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
            ParserParams parserParams = null;
            ColumnOrdering columnOrdering = null;

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

                        case "-q":
                            break;

                        default:
                            string option = args[i].Substring(1);
                            PropertyInfo prop = typeof(ParserParams).GetProperties().FirstOrDefault(f => f.Name == option);
                            if (prop != null)
                            {
                                if (parserParams == null)
                                {
                                    parserParams = new ParserParams();
                                }
                                if (i + 1 == args.Length)
                                {
                                    ShowHelp();
                                    return 1;
                                }

                                prop.SetValue(parserParams, args[++i], null);
                            }
                            else
                            {
                                Console.WriteLine("Invalid option " + args[i]);
                                return 1;
                            }
                            break;
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
                    Console.WriteLine("Unknown file extension " + extension);
                    return 1;
            }

            adapter.SetColumnOrdering(columnOrdering);

            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter, parserParams);

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

            Logger.Info("Parsing file " + declarationFile);
            Declaration declaration = parser.Parse();

            string output = DeclarationSerializer.Serialize(declaration, false);

            Logger.Info("Output size: " + output.Length);
            if (outFile != "")
            {
                Logger.Info("Writing json to " + outFile);
                File.WriteAllText(outFile, output);
            }

            return 0;
        }
    }

}
