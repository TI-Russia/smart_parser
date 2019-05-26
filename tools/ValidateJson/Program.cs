using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.DeclaratorApiClient;

namespace ValidateJson
{
    class Program
    {
        static void Main(string[] args)
        {
            string fileContents = File.ReadAllText(args[0]);
            Console.WriteLine(ApiClient.ValidateParserOutput(fileContents));
        }
    }
}
