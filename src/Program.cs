using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Smart.Parser.Adapters;
using Smart.Parser.Lib;

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
                                goto case "-h";
                            break;
                        case "-q":
                            break;

                        default:

                            Console.WriteLine("Invalid option " + args[i]);
                            return 1;
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

            string xlsxFile = declarationFile;
            IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);

            if (dumpColumn >= 0)
            {
                parser.DumpColumn(dumpColumn);
            }
            else { 
                parser.Process();
            }


            return 0;
        }
    }

}
