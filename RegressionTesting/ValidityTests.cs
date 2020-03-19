using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.Reflection;
using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;
using System.Text;
using System.Collections.Generic;

namespace RegressionTesting
{
    /// <summary>
    /// Summary description for ValidityTests
    /// </summary>
    [TestClass]
    public class ValidityTests
    {
        public ValidityTests()
        {
            //
            // TODO: Add constructor logic here
            //
        }

        private TestContext testContextInstance;

        /// <summary>
        ///Gets or sets the test context which provides
        ///information about and functionality for the current test run.
        ///</summary>
        public TestContext TestContext
        {
            get
            {
                return testContextInstance;
            }
            set
            {
                testContextInstance = value;
            }
        }

        #region Additional test attributes
        //
        // You can use the following additional attributes as you write your tests:
        //
        // Use ClassInitialize to run code before running the first test in the class
        // [ClassInitialize()]
        // public static void MyClassInitialize(TestContext testContext) { }
        //
        // Use ClassCleanup to run code after all tests in a class have run
        // [ClassCleanup()]
        // public static void MyClassCleanup() { }
        //
        // Use TestInitialize to run code before running each test 
        // [TestInitialize()]
        // public void MyTestInitialize() { }
        //
        // Use TestCleanup to run code after each test has run
        // [TestCleanup()]
        // public void MyTestCleanup() { }
        //
        #endregion
            
        private const string SmartParserLogFile = "smart_parser_files.log";

        private string SmartParserLogFilePath
        {
            get { return Path.GetFullPath(SmartParserLogFile); }
        }

        public String GetCanonFolder()
        {
            string solution_dir = Path.GetDirectoryName(Path.GetDirectoryName(TestContext.TestDir));
            if (solution_dir.EndsWith("RegressionTesting")) {
                return Path.Join(solution_dir, "files"); // for ubuntu dotnet
            }
            else {
                return Path.Join(solution_dir, "RegressionTesting", "files"); // in Windows Visual Studio
            }
        }


        public void TestSmartParserMultipleOut(string adapterName, string filename, params string[] outfiles)
        {
            SetupLog4Net();
            Smart.Parser.Adapters.AsposeLicense.SetAsposeLicenseFromEnvironment();
            Directory.CreateDirectory(Path.GetDirectoryName(filename));
            File.Copy(Path.Join(GetCanonFolder(), filename), filename, true);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", filename, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            Smart.Parser.Program.SkipRelativeOrphan = false;
            string outDir = Path.GetDirectoryName(Path.GetFullPath(filename));
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(filename);
            Smart.Parser.Program.ParseFile(filename, outFileName);
            foreach (var outfile in outfiles)
            {
                string expectedFile = Path.Combine(GetCanonFolder(), outfile);
                Assert.IsTrue(TestValidity(expectedFile, outfile, SmartParserLogFile));
            }
        }


        public void TestSmartParser(string filename, string adapterName, bool skipRelativeOrphan=false)
        {
            SetupLog4Net();
            Smart.Parser.Adapters.AsposeLicense.SetAsposeLicenseFromEnvironment();
            File.Copy(Path.Join(GetCanonFolder(), filename), filename, true);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", filename, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            Smart.Parser.Program.SkipRelativeOrphan = skipRelativeOrphan;
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(filename);
            string outDir = Path.GetDirectoryName(Path.GetFullPath(filename));
            Smart.Parser.Program.ParseFile(filename, outFileName);
            List<string> outFiles = new List<string>();
            if (File.Exists(outFileName))
                outFiles.Add(outFileName);
            else
            {
                string nameWithoutExtension = Path.GetFileNameWithoutExtension(outFileName);
                int i = 0;
                string fileName = $"{nameWithoutExtension}_{i}.json";
                while(File.Exists(fileName))
                {
                    outFiles.Add(fileName);
                    i++;
                    fileName = $"{nameWithoutExtension}_{i}.json";
                }
                if (outFiles.Count == 0)
                    throw new Exception($"Could not find output file");
            }
            List<string> expectedFileNames = outFiles.Select(x => Path.Combine(GetCanonFolder(), x)).ToList();
            for (int i = 0; i < outFiles.Count; i++)
            {
                Assert.IsTrue(TestValidity(expectedFileNames[i], outFiles[i], SmartParserLogFile));
            }
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinDalVostok2015()
        {
            TestSmartParser("MinDalVostok2015.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void TestPdfOneLine()
        {
            // from pdf
            TestSmartParser("one_line_2017.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void SpellCheckRealtyType()
        {
            TestSmartParser("SpellCheckRealtyType.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void TestPdfTwoTables()
        {
            // from pdf
            TestSmartParser("two_tables_2017.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void IncomeNotFirstLine()
        {
            TestSmartParser("IncomeNotFirstLine.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void SplitDeclarantAndRelatives()
        {
            TestSmartParser("4067_0.docx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void ManyManyColumns()
        {
            TestSmartParser("256_Columns.xlsx", "npoi");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void TestExcelMinfin2016()
        {
            TestSmartParser("minfin2016.xlsx", "npoi");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void TestMinZdrav2015()
        {
            TestSmartParser("minzdrav2015.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinSport2016()
        {
            TestSmartParser("MinSport2016.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinRes2011()
        {
            TestSmartParser("MinRes2011.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinYust2012()
        {
            TestSmartParser("MinYust2012.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void DepEnergo2010()
        {
            TestSmartParser("DepEnergo2010.doc", "prod");
        }


        [TestMethod]
        [TestCategory("docx")]
        public void MinZdorov2015Full()
        {
            TestSmartParser("MinZdorov2015Full.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkon2013()
        {
            TestSmartParser("MinEkon2013.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinStroy2014()
        {
            TestSmartParser("MinStroy2014.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinObr2012()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("MinObr2012.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinTrans2011()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("MinTrans2011.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinSevKavkaz2015()
        {
            // повтор Header внутри таблицы
            TestSmartParser("MinSevKavkaz2015.docx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinObr2016()
        {
            TestSmartParser("MinObr2016.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void Fsin2013()
        {
            TestSmartParser("fsin2013.docx", "prod") ;
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinStroy2017()
        {
            TestSmartParser("MinStroy2017.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinStroy2017_1()
        {
            //  Беру строки из середины файла
            TestSmartParser("MinStroy2017_1.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkonon2017()
        {
            TestSmartParser("MinEkonon2017.docx", "prod");
        }

        [TestMethod]
        [TestCategory("toloka")]
        public void TolokaGenerated()
        {
            TestSmartParser("toloka.toloka_json", "prod", true);
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void Unk2014()
        {
            TestSmartParser("Unk2014.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("xls")]
        public void File17207()
        {
            TestSmartParser("17207.xls", "prod");
        }

        [TestMethod]
        [TestCategory("toloka")]
        public void SectionExample()
        {
            TestSmartParser("section_example.toloka_json", "prod", true);
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinKult2015()
        {
            TestSmartParser("MinKult2015.docx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinDalVostok2017()
        {
            TestSmartParser("MinDalVostok2017.xlsx", "prod");
        }


        [TestMethod]
        [TestCategory("xlsx")]
        public void Rykovodstvo2013()
        {
            TestSmartParserMultipleOut("npoi", "9037\\rykovodstvo_2013.xlsx", "9037\\rykovodstvo_2013.xlsx_0.json", "9037\\rykovodstvo_2013.xlsx_1.json");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void Spasat2016()
        {
            TestSmartParser("Spasat2016.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void DepGosPol2012()
        {
            TestSmartParser("DepGosPol2012.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void TransposedTable()
        {
            TestSmartParser("30429.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void DividePersonAndRelativesByEoln()
        {
            TestSmartParser("8562.pdf.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void HeaderInsideTable()
        {
            TestSmartParser("HeaderInsideTable.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void dnko2014()
        {
            // внутри заголовка в таблице в конце написан бред, но падать не будем
            TestSmartParser("dnko-2014.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void ZagranApp2016()
        {
            // Column shift
            TestSmartParser("ZagranApp2016.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void BadColumnns()
        {
            TestSmartParser("BadColumns.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinKult2012()
        {
            TestSmartParser("MinKult2012.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinKult2011()
        {
            //error in vehicle column
            TestSmartParser("MinKult2011.doc", "prod", true);
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinSelhoz2015()
        {
            // повтор Header внутри таблицы
            TestSmartParser("MinSelhoz2015.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void Fsin2011()
        {
            TestSmartParser("Fsin2011.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkonom2014()
        {
            TestSmartParser("MinEkonom2014.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinProm2013()
        {
            TestSmartParser("MinProm2013.docx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinSelhoz2013()
        {
            TestSmartParser("MinSelhoz2013.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void ZabSud2017()
        {
            TestSmartParser("ZabSud2017.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void Mchs2010()
        {
            TestSmartParser("Mchs2010.doc", "prod");
        }

        [TestMethod]
        [TestCategory("xls")]
        public void MinObor2012()
        {
            TestSmartParser("MinObor2012.xls", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void Mchs2013()
        {
            TestSmartParser("Mchs2013.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinTrans2009()
        {
            TestSmartParser("MinTrans2009.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinKult2015Doc()
        {
            TestSmartParser("MinKult2015.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinKult2012doc()
        {
            TestSmartParser("MinKult2012.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkon2015()
        {
            TestSmartParser("MinEkon2015.docx", "prod");
        }

        [TestMethod]
        [TestCategory("htm")]
        public void Sudia2011()
        {
            TestSmartParser("Sudia2011.htm", "prod");
        }


        [TestMethod]
        [TestCategory("htm")]
        public void EmptyTablesInHtml()
        {
            TestSmartParser("7007_10.html", "prod");
        }


        [TestMethod]
        [TestCategory("htm")]
        public void ArbitrationCourt1()
        {
            TestSmartParser("17335_3.html", "prod");
        }

        
        [TestMethod]
        [TestCategory("htm")]
        public void ArbitrationCourt1TableLayout()
        {
            TestSmartParser("17339_24.html", "prod");
        }



        [TestMethod]
        [TestCategory("htm")]
        public void ArbitrationCourt2()
        {
            TestSmartParser("4144_28.htm", "prod");
        }

        [TestMethod]
        [TestCategory("htm")]
        public void PassStrangeTables()
        {
            TestSmartParser("4037_9.htm", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MergeByHyphen()
        {
            TestSmartParser("16694.docx", "prod");
        }

        [TestMethod]
        [TestCategory("htm")]
        public void ArbitrationCourtMariEl()
        {
            TestSmartParser("16738_12.html", "prod");
        }

        [TestMethod]
        [TestCategory("htm")]
        public void FederalAgencySubsoiUse2013()
        {
            TestSmartParser("15555_1.html", "prod");

        }

        private static void SetupLog4Net()
        {
            log4net.Repository.ILoggerRepository repo = log4net.LogManager.GetRepository(Assembly.GetEntryAssembly());
            log4net.Config.XmlConfigurator.Configure(repo, new FileInfo("log4net.config"));
            Parser.Lib.Logger.SetLogFileName("Main", "excel-parser-main.log");
            Parser.Lib.Logger.SetSecondLogFileName("excel-parser-aux.log");
            Parser.Lib.Logger.SetupForTests("Main", "Second");
        }

        public static string RunFileCompare(string expectedFile, string actualFile)
        {
            Process p = new Process();
            p.StartInfo.FileName = "fc.exe";
            p.StartInfo.Arguments = expectedFile + " " + actualFile;
            p.StartInfo.UseShellExecute = false;
            p.StartInfo.RedirectStandardOutput = true;
            p.Start();

            string output = p.StandardOutput.ReadToEnd();
            p.WaitForExit();
            byte[] data = p.StandardOutput.CurrentEncoding.GetBytes(output);
            string utf8 = Encoding.UTF8.GetString(data);

            return utf8;
        }

        private static bool TestValidity(string expectedFile, string actualFile, string logFile)
        {
            Log(logFile, ($"Running regression test on {actualFile}."));

            if (!File.Exists(expectedFile))
            {
                throw new FileNotFoundException($"Could not find expected output file {expectedFile}");
            }

            if (!File.Exists(actualFile))
            {
                throw new FileNotFoundException($"Could not find actual output file {actualFile}");
            }

            var actualOutput = File.ReadLines(actualFile);
            var expectedOutput = File.ReadLines(expectedFile);
            if (actualOutput.SequenceEqual(expectedOutput))
            {
                Log(logFile, "Actual output matches expected output (files are identical)");
                return true;
            }
            else
            {
                // lines in the files are numbered starting with 1, not 0
                // to make tracing changes in text editor or merge tool easier
                int lineNumber = 1;
                foreach (var zipLines in actualOutput.Zip(expectedOutput, Tuple.Create))
                {
                    if (zipLines.Item1 != zipLines.Item2)
                    {
                        Log(logFile, $"Expected and actual file differ. First mismatch on line {lineNumber}");
                        break;
                    }

                    lineNumber++;
                }

                if (actualOutput.Count() != expectedOutput.Count())
                {
                    Log(logFile, "Number of lines differs in expected and actual file");
                    Log(logFile, $"Expected number of lines: {expectedOutput.Count()}");
                    Log(logFile, $"Actual number of lines: {actualOutput.Count()}");
                }

                //string fcOut = RunFileCompare(expectedFile, actualFile);
                //Console.Write(fcOut);

                return false;
            }
        }

        private static void Log(string logFileName, string contents)
        {
            File.AppendAllText(logFileName, contents);
            File.AppendAllText(logFileName, "\n");
        }
    }
}