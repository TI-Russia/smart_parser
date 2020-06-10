using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Office.Interop.Word;
using Microsoft.Win32;
using System.Collections;

namespace MicrosoftPdf2Docx
{
    class TCharCategory {
        static string RUSSIAN = "ёйцукенгшщзхъфывапролджэячсмитьбю";
        static string LATIN = "qwertyuiopasdfghjklzxcvbnm";
        static string PUNCT = "\"'`@#$%^&*()`_+{}[]\\|;:'<>/?.,";
        static string DIGIT = "1234567890";
        static Hashtable _chardict = new Hashtable();

        public enum CHAR_TYPES : int
        {
            RUSSIAN_CHAR = 0,
            LATIN_CHAR = 1,
            PUNCT_CHAR = 2,
            DIGIT_CHAR = 3,
            OTHER_CHAR = 4,
            CHAR_TYPES_COUNT=5
        }
        static TCharCategory() {
            foreach (var x in RUSSIAN) {
                _chardict[x] = CHAR_TYPES.RUSSIAN_CHAR;
            }
            foreach (var x in LATIN)
            {
                _chardict[x] = CHAR_TYPES.LATIN_CHAR;
            }
            foreach (var x in PUNCT)
            {
                _chardict[x] = CHAR_TYPES.PUNCT_CHAR;
            }
            foreach (var x in DIGIT)
            {
                _chardict[x] = CHAR_TYPES.DIGIT_CHAR;
            }
        }

        public static int[] Classify(string text) {

            int[] res = new int [(int)CHAR_TYPES.CHAR_TYPES_COUNT];
            foreach (Char x in text) {
                Char lower_x = Char.ToLower(x);
                if (_chardict.ContainsKey(lower_x)) {
                    var char_class = _chardict[lower_x];
                    res[(int)char_class] += 1;
                }
                else
                {
                    res[(int)CHAR_TYPES.OTHER_CHAR] += 1;
                }
            }
            return res;
        }

        public static CHAR_TYPES GetMostPopupularCharCategory(string text) 
        {
            int[] classes = Classify(text);
            int max_value = 0;
            CHAR_TYPES max_class = CHAR_TYPES.OTHER_CHAR;
            for(int i = 0; i < classes.Length; ++i)
            {
                if (classes[i] > max_value)
                {
                    max_value = classes[i];
                    max_class = (CHAR_TYPES)i;
                }

            }
            return max_class;
        }
    }

    class WordDocument
    {
        public Document DocumentInstance = null;
        
        public void OpenDoc(Application wordApplication,  string filename)
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
        static bool SkipExisting = false;
        static string FailedFolder = null;
        static List<String> InputFiles = new List<String>();
        static Application WordApplication = null;

        static string GetTextFromDocumentWithoutSpaces(Document doc, int max_length)
        {
            string text = "";
            foreach (Range c in doc.Characters)
            {
                char c_char = (char)c.Text[0];
                if (Char.IsWhiteSpace(c_char)) continue;
                text += c_char;
                if (text.Length >= max_length) { break; }
            }
            return text;
        }

        static int GetMaxSquareImage(Document doc)
        {
            int max_square = 0;
            for (var i = 1; i <= doc.InlineShapes.Count; i++)
            {
                var inlineShape = doc.InlineShapes[i];
                int square = (int)inlineShape.Height * (int)inlineShape.Width;
                if (square > max_square)
                {
                    max_square = square;
                }
            }
            return max_square;
        }

        static bool CheckConversion(Document doc)
        {
            int max_text_size_without_spaces = 300;
            string text_start = GetTextFromDocumentWithoutSpaces(doc, max_text_size_without_spaces);
            if (text_start.Length < max_text_size_without_spaces)
            {
                Console.WriteLine(String.Format("text is too short (less than {0} chars)", max_text_size_without_spaces));
                return false;
            }
            if (TCharCategory.GetMostPopupularCharCategory(text_start) != TCharCategory.CHAR_TYPES.RUSSIAN_CHAR)
            {
                Console.WriteLine("it is not a Russian text, probably we cannot convert it properly");
                return false;
            }
            if (GetMaxSquareImage(doc) > 10000)
            {
                Console.WriteLine("document contains large images");
                return false;
            }
            return true;
        }

        public static void DeleteRegistryKey(string keyName)
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(keyName, true))
            {
                if (key != null)
                {
                    foreach (var v in key.GetValueNames())
                    {
                        key.DeleteValue(v, false);
                    }
                }
            }

        }

        public static void DeleteLastCrashedDialog()
        {
            try
            {
                string keyName =
                    @"Software\Microsoft\Office\"
                    + WordApplication.Version
                    + @"\Word\Resiliency\DisabledItems";
                DeleteRegistryKey(keyName);
            }
            catch (Exception)
            {

            }

        }

        static void ConvertFile(string inFilename, string outFileName)
        {
            string outFilePath = Path.GetFullPath(outFileName);
            DeleteLastCrashedDialog();
            var word_doc = new WordDocument();
            word_doc.OpenDoc(WordApplication, inFilename);

            bool can_convert = CheckConversion(word_doc.DocumentInstance);
            
            if (can_convert)
            {
                word_doc.DocumentInstance.SaveAs2(outFilePath, WdSaveFormat.wdFormatXMLDocument, CompatibilityMode: WdCompatibilityMode.wdWord2013);
            }

            word_doc.CloseDoc();

            if (can_convert) { 
                long length = new System.IO.FileInfo(outFilePath).Length;
                Console.WriteLine(String.Format("converted {0} to {1} outsize= {2}", inFilename, outFileName, length));
            }
        }

        static void CopyFailedDocx(string inFilename, string failed_folder)
        {
            var word_doc = new WordDocument();
            word_doc.OpenDoc(WordApplication, inFilename);
            bool can_convert = CheckConversion(word_doc.DocumentInstance);
            Console.WriteLine(String.Format("windord conversion for {0} is {1}", inFilename, can_convert));
            word_doc.CloseDoc();
            if (!can_convert)
            {
                string basename = System.IO.Path.GetFileName(inFilename);
                string targeFile = System.IO.Path.Combine(failed_folder, basename);
                Console.WriteLine(String.Format("copy {0} to {1}", inFilename, targeFile));
                System.IO.File.Copy(inFilename, targeFile, true);
            }
        }

        static CMDLine.CMDLineParser ParseArgs(string[] args)
        {
            CMDLine.CMDLineParser parser = new CMDLine.CMDLineParser();
            CMDLine.CMDLineParser.Option skipExistsOpt = parser.AddBoolSwitch("--skip-existing", "");
            CMDLine.CMDLineParser.Option failedFolderOpt = parser.AddStringParameter("--failed-folder", "", false);

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
            SkipExisting = skipExistsOpt.isMatched;
            if (failedFolderOpt.isMatched)
            {
                FailedFolder = failedFolderOpt.Value.ToString();
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
            //Thread.Sleep(3000);
        }

        static void ConvertFiles()
        {
            foreach (var f in InputFiles)
            {
                string pdf = f.Trim(new char[] { '"' });
                string winword = pdf + ".docx";
                if (SkipExisting && File.Exists(winword))
                {
                    Console.WriteLine(string.Format("skip creating {0}", winword));
                }
                else
                {
                    try
                    {
                        ConvertFile(pdf, winword);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("Error: " + ex.Message);
                    }
                }

            }
        }

        static void Main(string[] args)
        {
            CMDLine.CMDLineParser parser = ParseArgs(args);
            if (InputFiles.Count == 0) {
                Console.WriteLine("no input file");
                return;
            }
            OpenWinWord();
            if (FailedFolder != null)
            {
                foreach (var f in InputFiles)
                {
                    CopyFailedDocx(f, FailedFolder);
                }
            }
            else
            {
                ConvertFiles();
            }
            CloseWinWord();

        }
    }
}
