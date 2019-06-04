﻿using System;
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
using CMDLine;


namespace Smart.Parser
{
    public class Program
    {
        static string OutFile = "";
        static string AdapterFamily = "aspose";
        static bool ColumnsOnly = false;
        static bool CheckJson = false;

        static string ParseArgs(string[] args)
        {
            CMDLineParser parser = new CMDLineParser();
            CMDLineParser.Option outputOpt = parser.AddStringParameter("-o", "use file for output", false);
            CMDLineParser.Option licenseOpt = parser.AddStringParameter("-license", "", false);
            CMDLineParser.Option mainLogOpt = parser.AddStringParameter("-log", "", false);
            CMDLineParser.Option verboseOpt = parser.AddStringParameter("-v", "verbose level: debug, info, error", false);
            CMDLineParser.Option columnsOnlyOpt = parser.AddBoolSwitch("-columnsonly", "");
            CMDLineParser.Option checkJsonOpt = parser.AddBoolSwitch("-checkjson", "");
            CMDLineParser.Option adapterOpt = parser.AddStringParameter("-adapter", "can be aspose,npoi or microsoft, by default is aspose", false);
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
            if (licenseOpt.isMatched)
            {
                AsposeLicense.SetLicense(licenseOpt.Value.ToString());
            }
            string logFileName = "";
            if (mainLogOpt.isMatched)
            {
                logFileName = Path.GetFullPath(mainLogOpt.Value.ToString());
            }
            Logger.Setup(logFileName);
            if (outputOpt.isMatched)
            {
                OutFile = outputOpt.Value.ToString();
            }
            Logger.LogLevel verboseLevel = Logger.LogLevel.Info;
            if (verboseOpt.isMatched)
            {
                switch (verboseOpt.Value.ToString())
                {
                    case "info": verboseLevel = Logger.LogLevel.Info; break;
                    case "error": verboseLevel = Logger.LogLevel.Error; break;
                    case "debug": verboseLevel = Logger.LogLevel.Debug; break;
                    default:
                        {
                            throw new Exception("unknown verbose level "  + verboseOpt.Value.ToString());
                        }
                }

            }
            Logger.SetLoggingLevel(verboseLevel);

            if (adapterOpt.isMatched)
            {
                AdapterFamily = adapterOpt.Value.ToString();
                if (AdapterFamily != "aspose" && AdapterFamily != "npoi" && AdapterFamily != "microsoft")
                {
                    throw new Exception("unknown verbose adapter family " + AdapterFamily);
                }
            }

            ColumnsOnly = columnsOnlyOpt.isMatched;
            CheckJson = checkJsonOpt.isMatched;
            return  String.Join(" ", parser.RemainingArgs()).Trim(new char[] { '"' });
        }


        public static int Main(string[] args)
        {
            string declarationFile = ParseArgs(args);
            Logger.Info("Command line: " + String.Join(" ", args));
            if (String.IsNullOrEmpty(declarationFile))
            {
                Console.WriteLine("no input file or directory");
                return 1;
            }

            if (declarationFile.Contains("*") || declarationFile.Contains("?") || declarationFile.StartsWith("@"))
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
                Logger.Error("Parsing Exception " + e.ToString());
            }
            catch (Exception e)
            {
                Logger.Error("Unknown Parsing Exception " + e.ToString());
                //Logger.Info("Stack: " + e.StackTrace);
            }
            finally
            {
                Logger.SetOutMain();
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

        public static int ParseMultipleFiles(string fileMask)
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
                    Logger.Error("Parsing Exception " + e.ToString());
                    parse_results["exception"].Add(file);
                }
                catch (Exception e)
                {
                    caught = true;
                    Logger.Error("Parsing Exception " + e.ToString());
                    //Logger.Info("Stack: " + e.StackTrace);
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
                if (!caught && Logger.Errors.Count() > 0)
                {
                    Logger.Info("Result: error");
                    parse_results["error"].Add(file);
                }
                if (!caught && Logger.Errors.Count() == 0)
                {
                    Logger.Info("Result: OK");
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

            if (CheckJson && File.Exists(outFile))
            {
                Logger.Info("JSON file {0} already exist", outFile);
                return 0;

            }
            string logFile = Path.Combine(Path.GetDirectoryName(declarationFile), Path.GetFileName(declarationFile) + ".log");
            Logger.SetSecondLogFileName(Path.GetFullPath(logFile));

            Logger.Info(String.Format("Parsing {0}", declarationFile));

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
                    if (AdapterFamily == "aspose")
                    {
                        if (!AsposeLicense.Licensed && extension == ".xls")
                        {
                            throw new Exception("xls file format is not supported");
                        }
                        if (AsposeLicense.Licensed)
                        {
                            adapter = AsposeExcelAdapter.CreateAdapter(declarationFile);
                        }
                    }
                    else if (AdapterFamily == "npoi")
                    {
                        adapter = TI.Declarator.ExcelParser.XlsxParser.GetAdapter(declarationFile);
                    }
                    else
                    {
                        adapter = TI.Declarator.MicrosoftExcel.ExcelParser.GetAdapter(declarationFile);
                    }
                    break;
                default:
                    Logger.Error("Unknown file extension " + extension);
                    return 1;
            }
            if (adapter == null)
            {
                Logger.Error("Cannot find adapter for " + declarationFile);
                return 1;
            }
            if (adapter.GetWorkSheetCount() > 1)
            {
                Logger.Info(String.Format("File has multiple ({0}) worksheets", adapter.GetWorkSheetCount()));
                for (int sheetIndex = 0; sheetIndex < adapter.GetWorkSheetCount(); sheetIndex++)
                {
                    string curOutFile = outFile.Replace(".json", "_" + sheetIndex.ToString() + ".json");
                    Logger.Info(String.Format("Parsing worksheet {0} into file {1}", sheetIndex, curOutFile));
                    adapter.SetCurrentWorksheet(sheetIndex);
                    ParseOneFile(adapter, curOutFile);

                }
            }
            else
            {
                ParseOneFile(adapter, outFile);
            }
#if false
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
            if (ColumnsOnly)
                return 0;

            Declaration declaration = parser.Parse();

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

            Logger.Info("Writing json to " + outFile);
            File.WriteAllText(outFile, output);
#endif
            return 0;
        }

        public static int ParseOneFile(IAdapter adapter, string outFile)
        {
            Smart.Parser.Lib.Parser parser = new Smart.Parser.Lib.Parser(adapter);
            var columnOrdering = ColumnDetector.ExamineHeader(adapter);
            adapter.ColumnOrdering = columnOrdering;


            Logger.Info("Column ordering: ");
            foreach (var ordering in columnOrdering.ColumnOrder)
            {
                Logger.Info(ordering.ToString());
            }
            Logger.Info(String.Format("OwnershipTypeInSeparateField: {0}", columnOrdering.OwnershipTypeInSeparateField));
//            Logger.Info(String.Format("Parsing {0} Rows {1}", declarationFile, adapter.GetRowsCount()));
            if (ColumnsOnly)
                return 0;

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


            Declaration declaration = parser.Parse();

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

            Logger.Info("Writing json to " + outFile);
            File.WriteAllText(outFile, output);
            return 0;
        }

    }

}
