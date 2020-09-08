using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using System.Linq;
using SmartAntlr;
using Microsoft.VisualStudio.TestPlatform.ObjectModel;

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


        void TestCase(GeneralAntlrParserWrapper parser, string filename)
        {
            string input = Path.Join(GetTestFilesFolder(), filename);
            string output = input + ".result";
            var texts = AntlrCommon.ReadTestCases(input);
            AntlrCommon.WriteTestCaseResultsToFile(parser, texts, output);
            Assert.AreEqual(FileEquals(output, input + ".result.canon"), true);
        }

        [TestMethod]
        public void StrictParser()
        {
            TestCase(new AntlrStrictParser(), "strict.txt");
        }

        [TestMethod]
        public void SoupParser()
        {
            TestCase(new AntlrSoupParser(), "soup.txt");
        }

        [TestMethod]
        public void CountryList()
        {
            TestCase(new AntlrCountryListParser(), "country_list.txt");
        }
        [TestMethod]
        public void SquareList()
        {
            TestCase(new AntlrSquareParser(), "square_list.txt");
        }

        [TestMethod]
        public void SquareAndCountry()
        {
            var parser = new AntlrStrictParser();
            parser.StartFromRoot = AntlrStrictParser.StartFromRootEnum.square_and_country;
            TestCase(parser, "square_and_country.txt");
        }

    }

}
