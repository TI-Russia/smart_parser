using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.DeclaratorApiClient;

namespace DownloadPatterns
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine(ApiClient.DownloadPatterns());

        }
    }
}
