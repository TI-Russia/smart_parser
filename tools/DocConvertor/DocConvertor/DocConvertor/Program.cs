using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Office.Interop.Word;

namespace DocConvertor
{
    class Program
    {
        static void Main(string[] args)
        {
            Application word = new Application();
            try
            {
                var doc = word.Documents.Open(args[0], ReadOnly: true);
                for (int i = 0; i < doc.Paragraphs.Count; i++)
                {
                    string text = doc.Paragraphs[i + 1].Range.Text;
                    text = text.Replace("\n", " ").Replace("\t", " ").Replace("\r", " ").Trim();
                    Console.WriteLine(text);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine("{0} Exception caught.", e);
            }
            word.Quit();
        }
    }
}
