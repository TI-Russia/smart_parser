using System;
using System.Runtime.CompilerServices;
using CMDLine;
using SmartAntlr;
using System.Diagnostics;
using Microsoft.VisualStudio.TestPlatform.CommunicationUtilities.Interfaces;

namespace AntlrTester
{
    class Program
    {
        static string ParseType = "realty_all";
        static string ParseArgs(string[] args)
        {
            CMDLineParser parser = new CMDLineParser();
            CMDLineParser.Option typeOpt = parser.AddStringParameter("--type", "can bet realty_all, country, default is realty_all", false);
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
            if (typeOpt.isMatched)
            {
                ParseType = typeOpt.Value.ToString();
            }
            var freeArgs = parser.RemainingArgs();
            return String.Join(" ", freeArgs).Trim(new char[] { '"' });
        }

        static void Main(string[] args)
        {
            string input = ParseArgs(args);
            var output = input + ".result";
            var texts = AntlrCommon.ReadTestCases(input);
            GeneralAntlrParserWrapper parser = null;
            Console.Error.Write(String.Format("Grammar {0}\n", ParseType));
            if (ParseType == "realty_all")
            {
                parser = new AntlrStrictParser();
            }
            else if (ParseType == "country"  )
            {
                parser = new AntlrCountryListParser();
            }
            else
            {
                Debug.Assert(false);
            }
            parser.BeVerbose();
            AntlrCommon.WriteTestCaseResultsToFile(parser, texts, output);
        }
    }
}
