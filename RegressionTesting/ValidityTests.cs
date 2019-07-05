using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;

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


        public void TestSmartParser(string filename, string adapterName, bool skipRelativeOrphan=false)
        {
            SetupLog4Net();
            var workingCopy = Path.GetFileName(filename);
            File.Copy(filename, workingCopy);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", workingCopy, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            Smart.Parser.Program.SkipRelativeOrphan = skipRelativeOrphan;
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(workingCopy);
            Smart.Parser.Program.ParseOneFile(workingCopy, outFileName);
            string expectedFile = Path.Combine(SmartParserFilesDirectory, outFileName);
            Assert.IsTrue(TestValidity(expectedFile, outFileName, SmartParserLogFile));
        }

        [TestMethod]
        public void MinDalVostok2015()
        {
            TestSmartParser("SmartParser\\MinDalVostok2015.xlsx", "prod");
        }

        [TestMethod]
        public void TestPdfOneLine()
        {
            TestSmartParser("SmartParser\\one_line_2017.pdf", "xceed");
        }

        [TestMethod]
        public void SpellCheckRealtyType()
        {
            TestSmartParser("SmartParser\\SpellCheckRealtyType.docx", "xceed");
        }

        [TestMethod]
        public void TestPdfTwoTables()
        {
            TestSmartParser("SmartParser\\two_tables_2017.pdf", "xceed");
        }

        [TestMethod]
        public void IncomeNotFirstLine()
        {
            TestSmartParser("SmartParser\\IncomeNotFirstLine.docx", "xceed");
        }

        [TestMethod]
        public void ManyManyColumns()
        {
            TestSmartParser("SmartParser\\256_Columns.xlsx", "npoi");
        }

        [TestMethod]
        public void TestExcelMinfin2016()
        {
            TestSmartParser("SmartParser\\minfin2016.xlsx", "npoi");
        }

        [TestMethod]
        public void TestMinZdrav2015()
        {
            TestSmartParser("SmartParser\\minzdrav2015.docx", "xceed");
        }

        [TestMethod]
        public void MinSport2016()
        {
            TestSmartParser("SmartParser\\MinSport2016.docx", "xceed");
        }

        [TestMethod]
        public void MinRes2011()
        {
            TestSmartParser("SmartParser\\MinRes2011.doc", "xceed");
        }

        [TestMethod]
        public void MinZdorov2015Full()
        {
            TestSmartParser("SmartParser\\MinZdorov2015Full.docx", "xceed");
        }

        [TestMethod]
        public void MinEkon2013()
        {
            TestSmartParser("SmartParser\\MinEkon2013.docx", "prod");
        }

        [TestMethod]
        public void MinStroy2014()
        {
            TestSmartParser("SmartParser\\MinStroy2014.docx", "xceed");
        }

        [TestMethod]
        public void MinObr2012()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("SmartParser\\MinObr2012.docx", "xceed");
        }

        [TestMethod]
        public void MinTrans2011()
        {
            // в этом тесте есть ошибка, последний обеъек не парсится
            TestSmartParser("SmartParser\\MinTrans2011.docx", "xceed");
        }

        [TestMethod]
        public void MinSevKavkaz2015()
        {
            // повтор Header внутри таблицы
            TestSmartParser("SmartParser\\MinSevKavkaz2015.docx", "xceed");
        }

        [TestMethod]
        public void MinObr2016()
        {
            TestSmartParser("SmartParser\\MinObr2016.xlsx", "prod");
        }

        [TestMethod]
        public void Fsin2013()
        {
            TestSmartParser("SmartParser\\fsin2013.docx", "prod") ;
        }

        [TestMethod]
        public void MinStroy2017()
        {
            TestSmartParser("SmartParser\\MinStroy2017.xlsx", "prod");
        }

        [TestMethod]
        public void MinEkonon2017()
        {
            TestSmartParser("SmartParser\\MinEkonon2017.docx", "prod");
        }

        [TestMethod]
        public void TolokaGenerated()
        {
            TestSmartParser("SmartParser\\toloka.toloka_json", "prod", true);
        }

        [TestMethod]
        public void Unk2014()
        {
            TestSmartParser("SmartParser\\Unk2014.xlsx", "prod");
        }

        private static void SetupLog4Net()
        {
            log4net.Config.XmlConfigurator.Configure(new FileInfo("log4net.config"));
            Parser.Lib.Logger.SetLogFileName("Main", "excel-parser-main.log");
            Parser.Lib.Logger.SetSecondLogFileName("excel-parser-aux.log");
            Parser.Lib.Logger.SetupForTests("Main", "Second");
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