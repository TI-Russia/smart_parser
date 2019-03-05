using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using TI.Declarator.ParserCommon;
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

        private string WordLogFilePath
        {
            get { return Path.GetFullPath(WordLogFile); }
        }

        [TestMethod]
        [DeploymentItem(SamplesDirectory)]
        [DeploymentItem("PropertyDictionary.txt")]
        [DeploymentItem("import-schema.json")]
        [DeploymentItem("import-schema-dicts.json")]
        public void TestWordParser()
        {
            int nFailedComparisons = 0;
            foreach (var filename in Directory.GetFiles(WordFilesDirectory, "*.docx"))
            {
                Declaration res = Tindalos.Tindalos.Process(filename);
                string outputFileName = Path.GetFileNameWithoutExtension(filename) + ".json";
                File.WriteAllText(outputFileName, DeclarationSerializer.Serialize(res));

                string expectedFile = Path.Combine(WordFilesDirectory, outputFileName);
                bool isValid = TestValidity(expectedFile, outputFileName, WordLogFile);

                if (!isValid) { nFailedComparisons++; }
            }

            Assert.AreEqual(0, nFailedComparisons, $"{nFailedComparisons} output files are not valid. Comparison log can be found in {WordLogFilePath}");
        }

        private static bool TestValidity(string expectedFile, string actualFile, string logFile)
        {
            Console.WriteLine($"Running regression test on {actualFile}.");

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

        private static void Log(string logFileName, string contents)
        {
            File.AppendAllText(logFileName, contents);
            File.AppendAllText(logFileName, "\n");
        }
    }
}
