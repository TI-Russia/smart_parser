using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using System.Linq;
using SmartAntlr;

namespace test
{
    [TestClass]
    public class AntlrTest
    {
        static bool FileEquals(string path1, string path2)
        {
            return File.ReadAllBytes(path1).SequenceEqual(File.ReadAllBytes(path2));
        }

        public String GetTestFilesFolder()
        {
            var curDir = Directory.GetCurrentDirectory();
            while (curDir.Length > 3 && Path.GetFileName(curDir) != "Antlr")
            {
                curDir = Path.GetDirectoryName(curDir);
            }
            if (curDir.Length <= 3)
            {
                throw new Exception("cannot find folder with test_files");
            }
            return Path.Join(curDir, "test_files");
        }


        [TestMethod]
        public void TestRealtyAll()
        {
            string input = Path.Join(GetTestFilesFolder(), "realty_all.txt");
            string output = input + ".result";
            var texts = AntlrCommon.ReadTestCases(input);
            AntlrCommon.WriteTestCaseResultsToFile(new AntlrRealtyParser(), texts, output);
            Assert.AreEqual(FileEquals(output, input + ".result.canon"), true);
        }

        [TestMethod]
        public void TestCountries()
        {
            string input = Path.Join(GetTestFilesFolder(), "country.txt");
            string output = input + ".result";
            var texts = AntlrCommon.ReadTestCases(input);
            AntlrCommon.WriteTestCaseResultsToFile(new AntlrCountryParser(), texts, output);
            Assert.AreEqual(FileEquals(output, input + ".result.canon"), true);
        }
    }

}
