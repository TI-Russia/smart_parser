using System;
using Smart.Parser.Adapters;
using System.Diagnostics;
using System.IO;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using System.Text;

namespace Office2Txt
{
    class Program
    {
        static string ProcessDocxPart(OpenXmlPartRootElement part)
        {
            var s = new StringBuilder();
            foreach (var p in part.Descendants<Paragraph>())
            {
                s.Append(p.InnerText).Append('\n');
            }
            return s.ToString();
        }
        static string ProcessDocx(string inputFile)
        {
            WordprocessingDocument doc =
                WordprocessingDocument.Open(inputFile, false);
            var s = new StringBuilder();
            foreach (OpenXmlPart h in doc.MainDocumentPart.HeaderParts) {
                s.Append(ProcessDocxPart(h.RootElement));
            };
            s.Append(ProcessDocxPart(doc.MainDocumentPart.Document));
            doc.Close();
            return s.ToString();
        }
        static void Main(string[] args)
        {
            Smart.Parser.Adapters.AsposeLicense.SetAsposeLicenseFromEnvironment();
            Debug.Assert(args.Length == 2);            
            string  inputFile = args[0];
            string outFile = args[1];
            string extension = Path.GetExtension(inputFile).ToLower();
            string text = "";
            if (extension == ".docx")
            {
                text = ProcessDocx(inputFile);
            }
            else
            {
                Console.WriteLine("cannot process " + inputFile);
                Environment.Exit(1);
            }
            File.WriteAllText(outFile, text);
        }
    }
}
