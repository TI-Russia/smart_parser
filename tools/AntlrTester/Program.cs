using System;

namespace AntlrTester
{
    class Program
    {
        static void Main(string[] args)
        {
            var input = args[0];
            var output = input + ".result";
            var texts = AntlrTestUtilities.ReadTestCases(input);
            AntlrTestUtilities.ProcessTestCases(texts, output);
        }
    }
}
