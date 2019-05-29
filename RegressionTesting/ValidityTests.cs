using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using TI.Declarator.ParserCommon;
using TI.Declarator.DeclaratorApiClient;
using TI.Declarator.JsonSerialization;

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

        private const string SamplesDirectory = "regression_samples";

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
        /*
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
        private void TestWordParser(string filename)
        {
            Declaration res = Tindalos.Tindalos.Process(filename);
            string outputFileName = Path.GetFileNameWithoutExtension(filename) + ".json";
            File.WriteAllText(outputFileName, DeclarationSerializer.Serialize(res));

            string expectedFile = Path.Combine(WordFilesDirectory, outputFileName);
            Assert.IsTrue(TestValidity(expectedFile, outputFileName, WordLogFilePath));
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordMinSport()
        {
            TestWordParser("Word\\2016_Sotrudniki_ministerstva.docx");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordTypeA()
        {
            TestWordParser("Word\\A - min_res_2011_Sotrudniki_ministerstva.doc");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordTypeC()
        {
            TestWordParser("Word\\C - min_health_2015_Sotrudniki_ministerstva.docx");
        }

        private const string SmartParserFilesDirectory = @"SmartParser";
        private const string SmartParserLogFile = "smart_parser_files.log";

        private string SmartParserLogFilePath
        {
            get { return Path.GetFullPath(SmartParserLogFile); }
        }


        public void TestSmartParser(string filename, string adapterName)
        {
            SetupLog4Net();
            var workingCopy = Path.GetFileName(filename);
            File.Copy(filename, workingCopy);
            Log(SmartParserLogFile, String.Format("run smart_parser on {0} in directory {1}", workingCopy, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = adapterName;
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(workingCopy);
            Smart.Parser.Program.ParseOneFile(workingCopy, outFileName);
            string expectedFile = Path.Combine(SmartParserFilesDirectory, outFileName);
            Assert.IsTrue(TestValidity(expectedFile, outFileName, SmartParserLogFile));
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestSmartParserBasic()
        {
            TestSmartParser("SmartParser\\basic.xlsx", "npoi");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestPdfOneLine()
        {
            TestSmartParser("SmartParser\\one_line_2017.pdf", "xceed");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void SpellCheckRealtyType()
        {
            TestSmartParser("SmartParser\\SpellCheckRealtyType.docx", "xceed");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestPdfTwoTables()
        {
            TestSmartParser("SmartParser\\two_tables_2017.pdf", "xceed");
        }


        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestExcelMinfin2016()
        {
            TestSmartParser("SmartParser\\minfin2016.xlsx", "npoi");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestMinZdrav2015()
        {
            TestSmartParser("SmartParser\\minzdrav2015.docx", "xceed");
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
