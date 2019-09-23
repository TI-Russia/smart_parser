using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;
using System.Text;

namespace RegressionTesting
{
    /// <summary>
    /// Summary description for ValidityTests
    /// </summary>
    [TestClass]
    [DeploymentItem(SamplesDirectory)]
    [DeploymentItem(@"JsonSerialization\import-schema.json")]
    [DeploymentItem(@"JsonSerialization\import-schema-dicts.json")]
    [DeploymentItem("log4net.config")]
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
            
        private const string SamplesDirectory = "regression_samples";
        /*
        private const string WordFilesDirectory = @"Word";
        private const string WordLogFile = "word_files.log";
        private const string SampleWordLogFile = "sample_word_files.log";

        private string WordLogFilePath
        {
            get { return Path.GetFullPath(WordLogFile); }
        }

        private string SampleWordLogFilePath
        {
            get { return Path.GetFullPath(SampleWordLogFile); }
        }
        
         все время сломан - пока отключаем
        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordSampleFiles()
        {
            int nChecks = 0;
            int nFailedChecks = 0;
            foreach (var sampleFile in Directory.GetFiles(WordFilesDirectory, "*.json"))
            {
                nChecks++;
                if (!IsSampleFileValid(sampleFile, SampleWordLogFilePath))
                {
                    nFailedChecks++;
                }
            }

            Assert.AreEqual(0, nFailedChecks, $"Sample files validation test: {nFailedChecks} out of {nChecks} sample files are not valid. Validation log can be found in {SampleWordLogFilePath}");
        }
        */
        private const string SmartParserFilesDirectory = @"SmartParser";
        private const string SmartParserLogFile = "smart_parser_files.log";

        private string SmartParserLogFilePath
        {
            get { return Path.GetFullPath(SmartParserLogFile); }
        }


        public void TestSmartParserMultipleOut(string adapterName, string filename, params string[] outfiles)
        {
            SetupLog4Net();
            Smart.Parser.Program.SetAsposeLicenseFromEnvironment();
            var workingCopy = Path.GetFileName(filename);
            File.Copy(filename, workingCopy);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", workingCopy, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            Smart.Parser.Program.SkipRelativeOrphan = false;
            string outDir = Path.GetDirectoryName(Path.GetFullPath(workingCopy));
            Smart.Parser.Adapters.IAdapter.ConvertedFileDir = outDir;
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(workingCopy);
            Smart.Parser.Program.ParseFile(filename, outFileName);
            foreach (var outfile in outfiles)
            {
                string expectedFile = Path.Combine(SmartParserFilesDirectory, outfile);
                Assert.IsTrue(TestValidity(expectedFile, outfile, SmartParserLogFile));
            }
        }


        public void TestSmartParser(string filename, string adapterName, bool skipRelativeOrphan=false)
        {
            SetupLog4Net();
            Smart.Parser.Program.SetAsposeLicenseFromEnvironment();
            var workingCopy = Path.GetFileName(filename);
            File.Copy(filename, workingCopy);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", workingCopy, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            Smart.Parser.Program.SkipRelativeOrphan = skipRelativeOrphan;
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(workingCopy);
            string outDir = Path.GetDirectoryName(Path.GetFullPath(workingCopy));
            Smart.Parser.Adapters.IAdapter.ConvertedFileDir = outDir;
            Smart.Parser.Program.ParseFile(workingCopy, outFileName);
            //string expectedFile = Path.Combine(SmartParserFilesDirectory, Path.GetFileNameWithoutExtension(workingCopy) + ".json");
            string expectedFile = Path.Combine(SmartParserFilesDirectory, outFileName);
            Assert.IsTrue(TestValidity(expectedFile, outFileName, SmartParserLogFile));
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinDalVostok2015()
        {
            TestSmartParser("SmartParser\\MinDalVostok2015.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("pdf")]
        public void TestPdfOneLine()
        {
            TestSmartParser("SmartParser\\one_line_2017.pdf", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void SpellCheckRealtyType()
        {
            TestSmartParser("SmartParser\\SpellCheckRealtyType.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("pdf")]
        public void TestPdfTwoTables()
        {
            TestSmartParser("SmartParser\\two_tables_2017.pdf", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void IncomeNotFirstLine()
        {
            TestSmartParser("SmartParser\\IncomeNotFirstLine.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void ManyManyColumns()
        {
            TestSmartParser("SmartParser\\256_Columns.xlsx", "npoi");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void TestExcelMinfin2016()
        {
            TestSmartParser("SmartParser\\minfin2016.xlsx", "npoi");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void TestMinZdrav2015()
        {
            TestSmartParser("SmartParser\\minzdrav2015.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinSport2016()
        {
            TestSmartParser("SmartParser\\MinSport2016.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinRes2011()
        {
            TestSmartParser("SmartParser\\MinRes2011.doc", "xceed");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinYust2012()
        {
            TestSmartParser("SmartParser\\MinYust2012.doc", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void DepEnergo2010()
        {
            TestSmartParser("SmartParser\\DepEnergo2010.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinZdorov2015Full()
        {
            TestSmartParser("SmartParser\\MinZdorov2015Full.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkon2013()
        {
            TestSmartParser("SmartParser\\MinEkon2013.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinStroy2014()
        {
            TestSmartParser("SmartParser\\MinStroy2014.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinObr2012()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("SmartParser\\MinObr2012.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinTrans2011()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("SmartParser\\MinTrans2011.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinSevKavkaz2015()
        {
            // повтор Header внутри таблицы
            TestSmartParser("SmartParser\\MinSevKavkaz2015.docx", "xceed");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinObr2016()
        {
            TestSmartParser("SmartParser\\MinObr2016.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void Fsin2013()
        {
            TestSmartParser("SmartParser\\fsin2013.docx", "prod") ;
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinStroy2017()
        {
            TestSmartParser("SmartParser\\MinStroy2017.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinEkonon2017()
        {
            TestSmartParser("SmartParser\\MinEkonon2017.docx", "prod");
        }

        [TestMethod]
        [TestCategory("toloka")]
        public void TolokaGenerated()
        {
            TestSmartParser("SmartParser\\toloka.toloka_json", "prod", true);
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void Unk2014()
        {
            TestSmartParser("SmartParser\\Unk2014.xlsx", "prod");
        }

        [TestMethod]
        [TestCategory("xls")]
        public void File17207()
        {
            TestSmartParser("SmartParser\\17207.xls", "prod");
        }

        [TestMethod]
        [TestCategory("toloka")]
        public void SectionExample()
        {
            TestSmartParser("SmartParser\\section_example.toloka_json", "prod", true);
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinKult2015()
        {
            TestSmartParser("SmartParser\\MinKult2015.docx", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void MinDalVostok2017()
        {
            TestSmartParser("SmartParser\\MinDalVostok2017.xlsx", "prod");
        }


        [TestMethod]
        [TestCategory("xlsx")]
        public void Rykovodstvo2013()
        {
            TestSmartParserMultipleOut("npoi", "SmartParser\\9037\\rykovodstvo_2013.xlsx", "rykovodstvo_2013.xlsx_0.json", "rykovodstvo_2013.xlsx_1.json");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void Spasat2016()
        {
            TestSmartParser("SmartParser\\Spasat2016.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void DepGosPol2012()
        {
            TestSmartParser("SmartParser\\DepGosPol2012.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void HeaderInsideTable()
        {
            TestSmartParser("SmartParser\\HeaderInsideTable.docx", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void dnko2014()
        {
            // внутри заголовка в таблице в конце написан бред, но падать не будем
            TestSmartParser("SmartParser\\dnko-2014.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void ZagranApp2016()
        {
            TestSmartParser("SmartParser\\ZagranApp2016.doc", "prod");
        }

        [TestMethod]
        [TestCategory("xlsx")]
        public void BadColumnns()
        {
            TestSmartParser("SmartParser\\BadColumns.doc", "prod");
        }

        [TestMethod]
        [TestCategory("docx")]
        public void MinKult2012()
        {
            TestSmartParser("SmartParser\\MinKult2012.docx", "prod");
        }

        [TestMethod]
        [TestCategory("doc")]
        public void MinKult2011()
        {
            //error in vehicle column
            TestSmartParser("SmartParser\\MinKult2011.doc", "prod", true);
        }


        private static void SetupLog4Net()
        {
            log4net.Config.XmlConfigurator.Configure(new FileInfo("log4net.config"));
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

                string fcOut = RunFileCompare(expectedFile, actualFile);
                Console.Write(fcOut);

                return false;
            }
        }

        private static bool IsSampleFileValid(string expectedFile, string logFile)
        {
            string expectedOutput = File.ReadAllText(expectedFile);
            string validationResult = ApiClient.ValidateParserOutput(expectedOutput);

            if (validationResult != "[]")
            {
                string errorsFileName = "errors_" + Path.GetFileNameWithoutExtension(expectedFile) + ".json";
                File.WriteAllText(errorsFileName, validationResult);
                Log(logFile, $"Expected file {expectedFile} is no longer valid." +
                    $" Please ensure it conforms to the latest schema and validation requirements.");
                Log(logFile, $"Validation errors are listed in {Path.GetFullPath(errorsFileName)}");

                return false;
            }

            return true;
        }

        private static void Log(string logFileName, string contents)
        {
            File.AppendAllText(logFileName, contents);
            File.AppendAllText(logFileName, "\n");
        }
    }
}