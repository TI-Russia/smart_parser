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

    class Program
    {
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
                string wordVersion;
                Application word = new Application();
                wordVersion = word.Version;
                word.Quit();
                string keyName =
                    @"Software\Microsoft\Office\"
                    + wordVersion
                    + @"\Word\Resiliency\DisabledItems";
                DeleteRegistryKey(keyName);
            }
            catch (Exception)
            {

            }

        }

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

        static void ConvertFile(string inFilename, string outFileName)
        {
            
            DeleteLastCrashedDialog();
            Application word = new Application();
            var doc = word.Documents.OpenNoRepairDialog(
                Path.GetFullPath(inFilename),
                ReadOnly: true,
                ConfirmConversions: false,
                OpenAndRepair: false);
            int max_text_size_without_spaces = 300;
            string text_start = GetTextFromDocumentWithoutSpaces(doc, max_text_size_without_spaces);
            if (text_start.Length < max_text_size_without_spaces)
            {
                Console.WriteLine(String.Format("text is too short (less than {0} chars)", max_text_size_without_spaces));
                return;
            }
            if (TCharCategory.GetMostPopupularCharCategory(text_start) != TCharCategory.CHAR_TYPES.RUSSIAN_CHAR)
            {
                Console.WriteLine("it is not a Russian text, probably we cannot convert it properly");
                return;
            }
            if (GetMaxSquareImage(doc) > 10000)
            {
                Console.WriteLine("document contains large images");
                return;
            }
            var outFilePath = Path.GetFullPath(outFileName);
            doc.SaveAs2(outFilePath, WdSaveFormat.wdFormatXMLDocument, CompatibilityMode: WdCompatibilityMode.wdWord2013);
            word.ActiveDocument.Close();
            word.Quit(SaveChanges: WdSaveOptions.wdDoNotSaveChanges);
            System.GC.Collect();
            System.GC.WaitForPendingFinalizers();
            long length = new System.IO.FileInfo(outFilePath).Length;
            Console.WriteLine(String.Format("converted {0} to {1} outsize= {2}", inFilename, outFileName, length));
        }

        static void Main(string[] args)
        {
            CMDLine.CMDLineParser parser = new CMDLine.CMDLineParser();
            CMDLine.CMDLineParser.Option skipExistsOpt = parser.AddBoolSwitch("--skip-existing", "");
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
            var files = parser.RemainingArgs();
            if (files == null) {
                Console.WriteLine("no input file");
            } else
            {
                foreach (var f in files)
                {
                    string pdf = f.Trim(new char[] { '"' });
                    string winword = pdf + ".docx";
                    if (skipExistsOpt.isMatched && File.Exists(winword))
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

        }
    }
}
