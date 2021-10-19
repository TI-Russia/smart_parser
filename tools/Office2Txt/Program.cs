using SmartParser.Lib;

using System;
using System.Diagnostics;
using System.IO;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;

namespace Office2Txt
{
    class Program
    {
        static string ProcessDocxPart(OpenXmlPartRootElement part)
        {
            string s = "";
            foreach (var p in part.Descendants<Paragraph>())
            {
                s += p.InnerText + "\n";
            }
            return s;
        }
        static string ProcessDocx(string inputFile)
        {
            WordprocessingDocument doc =
                WordprocessingDocument.Open(inputFile, false);
            string s = "";
            foreach (OpenXmlPart h in doc.MainDocumentPart.HeaderParts) {
                s += ProcessDocxPart(h.RootElement);
            };
            s += ProcessDocxPart(doc.MainDocumentPart.Document);
            doc.Close();
            return s;
        }
        static void Main(string[] args)
        {
            SmartParser.Lib.AsposeLicense.SetAsposeLicenseFromEnvironment();
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
