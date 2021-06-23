using System;
using System.IO;
using Microsoft.Office.Interop.Word;
using System.Linq;
using System.Text;
using System.Collections.Generic;


namespace DocxFont
{
    class WordDocument
    {
        public Document DocumentInstance = null;

        public void OpenDoc(Application wordApplication, string filename)
        {
            DocumentInstance = wordApplication.Documents.OpenNoRepairDialog(
                Path.GetFullPath(filename),
                ReadOnly: true,
                ConfirmConversions: false,
                OpenAndRepair: false);
        }
        public void CloseDoc()
        {
            DocumentInstance.Close();
            DocumentInstance = null;
        }


    }
    class Program
    {
        static List<String> InputFiles = new List<String>();
        static Application WordApplication = null;
        static CMDLine.CMDLineParser ParseArgs(string[] args)
        {
            CMDLine.CMDLineParser parser = new CMDLine.CMDLineParser();

            parser.AddHelpOption();
            try
            {
                parser.Parse(args);
            }
            catch (Exception ex)
            {
                //show available options      
                Console.Write(parser.HelpMessage());
                Console.WriteLine();
                Console.WriteLine("Error: " + ex.Message);
                throw;
            }
            foreach (var f in parser.RemainingArgs())
            {
                if (File.Exists(f))
                {
                    InputFiles.Add(f);
                }
            }
            return parser;
        }
        static void OpenWinWord()
        {
            WordApplication = new Application();
        }
        static void CloseWinWord()
        {
            WordApplication.Quit(SaveChanges: WdSaveOptions.wdDoNotSaveChanges);
            WordApplication = null;
            System.GC.Collect();
            System.GC.WaitForPendingFinalizers();
            WordApplication = null;
        }


        static void PrintFonts(string inFilename)
        {
            var word_doc = new WordDocument();
            word_doc.OpenDoc(WordApplication, inFilename);
            var fontFrequency = new Dictionary<string, int>();
            foreach (Range c in word_doc.DocumentInstance.Characters)
            {
                var font = c.Font;
                var key = String.Format("{0} {1}", font.Name, font.Size);
                if (!fontFrequency.ContainsKey(key))
                {
                    fontFrequency.Add(key, 0);
                }
                fontFrequency[key] += c.Characters.Count;
                
            }
            foreach (var key_value in fontFrequency)
            {
                Console.WriteLine("{0} {1}", key_value.Key, key_value.Value);
            }
            word_doc.CloseDoc();
        }

        static void Main(string[] args)
        {
            CMDLine.CMDLineParser parser = ParseArgs(args);
            if (InputFiles.Count == 0)
            {
                Console.WriteLine("no input file");
                return;
            }
            OpenWinWord();
            foreach (var f in InputFiles)
            {
                PrintFonts(f);
            }
            CloseWinWord();

        }
    }
}
