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

                        case "-q":
                            break;

                    }
                }
                if (declarationFile == string.Empty)
                    declarationFile = args[i];
                else
                {
                    ShowHelp();
                    return 1;
                }

            }

            string xlsxFile = declarationFile;
            IAdapter adapter = AsposeExcelAdapter.CreateAsposeExcelAdapter(xlsxFile);
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);

            parser.Process();


            return 0;
        }
    }

}
