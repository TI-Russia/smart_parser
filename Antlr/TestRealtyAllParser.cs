using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;
using System.Linq;


namespace test
{
    [TestClass]
    public class AntlrRealtyAllTest
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
        public void TestSimple()
        {
            string input = Path.Join(GetTestFilesFolder(), "realty_all.txt");
            string output = input + ".result";
            var texts = AntlrTestUtilities.ReadTestCases(input);

            if (File.Exists(output))
            {
                File.Delete(output);
            }
            AntlrTestUtilities.ProcessTestCases(texts, output);
            Assert.AreEqual(FileEquals(output, input + ".result.canon"), true);
        }

    }
    
}
