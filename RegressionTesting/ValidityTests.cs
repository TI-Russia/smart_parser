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
        public void TestWordMinRes()
        {
            TestWordParser("Word\\A - min_res_2011_Sotrudniki_ministerstva.doc");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordMinHealth()
        {
            TestWordParser("Word\\C - min_health_2015_Sotrudniki_ministerstva.docx");
        }

        private const string ExcelFilesDirectory = @"Excel";
        private const string ExcelLogFile = "excel_files.log";

        private string ExcelLogFilePath
        {
            get { return Path.GetFullPath(ExcelLogFile); }
        }


        public void TestExcelParser(string filename)
        {
            SetupLog4Net();
            var workingCopy = Path.GetFileName(filename);
            File.Copy(filename, workingCopy);
            Log(ExcelLogFile, String.Format("run smart_parser on {0} in directory {1}", workingCopy, Directory.GetCurrentDirectory()));
            Smart.Parser.Program.AdapterFamily = "npoi";
            string outFileName = Smart.Parser.Program.BuildOutFileNameByInput(workingCopy);
            Smart.Parser.Program.ParseOneFile(workingCopy, outFileName);
            string expectedFile = Path.Combine(ExcelFilesDirectory, outFileName);
            Assert.IsTrue(TestValidity(expectedFile, outFileName, ExcelLogFile));
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestExcelParserBasic()
        {
            TestExcelParser("Excel\\basic.xlsx");
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("log4net.config")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestExcelMinfin2016()
        {
            TestExcelParser("Excel\\minfin2016.xlsx");
        }

        private const string PdfFilesDirectory = @"Pdf";
        private const string PdfLogFile = "pdf_files.log";
        private string PdfLogFilePath
        {
            get { return Path.GetFullPath(PdfLogFile); }
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestPdfParser()
        {
            int nFailedComparisons = 0;
            int nComparisons = 0;
            foreach (var filename in Directory.GetFiles(PdfFilesDirectory, "*.pdf"))
            {
                Declaration res = Tindalos.Tindalos.Process(filename);
                string outputFileName = Path.GetFileNameWithoutExtension(filename) + ".json";
                File.WriteAllText(outputFileName, DeclarationSerializer.Serialize(res));

                string expectedFile = Path.Combine(PdfFilesDirectory, outputFileName);
                bool isValid = TestValidity(expectedFile, outputFileName, PdfLogFilePath);

                if (!isValid) { nFailedComparisons++; }
                nComparisons++;
            }

            Assert.AreEqual(0, nFailedComparisons, $"pdf parser test: {nFailedComparisons} out of {nComparisons} output files are not valid. Comparison log can be found in {PdfLogFilePath}");
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
