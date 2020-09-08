using System.Xml.Linq;
using System.IO.Compression;
using System.Threading;
using System.IO;
using System;
using System.Linq;
using System.Xml;
using System.Security.Cryptography;
using System.Text;
using System.Net;
using Parser.Lib;
using System.Runtime.InteropServices;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    public class ConversionServerClient : WebClient
    {
        protected override WebRequest GetWebRequest(Uri uri)
        {
            WebRequest w = base.GetWebRequest(uri);
            w.Timeout = 5 * 60 *  1000; // 5 minutes
            return w;
        }
    }
    public static class UriFixer
    {
        public static void FixInvalidUri(Stream fs, Func<string, Uri> invalidUriHandler)
        {
            XNamespace relNs = "http://schemas.openxmlformats.org/package/2006/relationships";
            using (ZipArchive za = new ZipArchive(fs, ZipArchiveMode.Update))
            {
                foreach (var entry in za.Entries.ToList())
                {
                    if (!entry.Name.EndsWith(".rels"))
                        continue;
                    bool replaceEntry = false;
                    XDocument entryXDoc = null;
                    using (var entryStream = entry.Open())
                    {
                        try
                        {
                            entryXDoc = XDocument.Load(entryStream);
                            if (entryXDoc.Root != null && entryXDoc.Root.Name.Namespace == relNs)
                            {
                                var urisToCheck = entryXDoc
                                    .Descendants(relNs + "Relationship")
                                    .Where(r => r.Attribute("TargetMode") != null && (string)r.Attribute("TargetMode") == "External");
                                foreach (var rel in urisToCheck)
                                {
                                    var target = (string)rel.Attribute("Target");
                                    if (target != null)
                                    {
                                        try
                                        {
                                            Uri uri = new Uri(target);
                                        }
                                        catch (UriFormatException)
                                        {
                                            Uri newUri = invalidUriHandler(target);
                                            rel.Attribute("Target").Value = newUri.ToString();
                                            replaceEntry = true;
                                        }
                                    }
                                }
                            }
                        }
                        catch (XmlException)
                        {
                            continue;
                        }
                    }
                    if (replaceEntry)
                    {
                        var fullName = entry.FullName;
                        entry.Delete();
                        var newEntry = za.CreateEntry(fullName);
                        using (StreamWriter writer = new StreamWriter(newEntry.Open()))
                        using (XmlWriter xmlWriter = XmlWriter.Create(writer))
                        {
                            entryXDoc.WriteTo(xmlWriter);
                        }
                    }
                }
            }
        }
    }
    public class DocxConverter
    {
        string DeclaratorConversionServerUrl;
        public DocxConverter(string declaratorConversionServerUrl)
        {
            DeclaratorConversionServerUrl = declaratorConversionServerUrl;
        }
        private static string ToHex(byte[] bytes)
        {
            StringBuilder result = new StringBuilder(bytes.Length * 2);

            for (int i = 0; i < bytes.Length; i++)
                result.Append(bytes[i].ToString("x2"));

            return result.ToString();
        }

        public string DowloadFromConvertedStorage(string filename)
        {
            using (SHA256 mySHA256 = SHA256.Create())
            {
                string hashValue;
                using (FileStream fileStream = File.Open(filename, FileMode.Open))
                {
                    hashValue = ToHex(mySHA256.ComputeHash(fileStream));
                }
                using (var client = new ConversionServerClient())
                {
                    string url = DeclaratorConversionServerUrl + "?sha256=" + hashValue;
                    if (!url.StartsWith("http://"))
                    {
                        url = "http://" + url;
                    }
                    string docXPath = Path.GetTempFileName();
                    Logger.Debug(String.Format("try to download docx from {0} to {1}", url, docXPath));

                    try
                    {
                        client.DownloadFile(url, docXPath);
                        Logger.Debug("WebClient.DownloadFile downloaded file successfully");
                        Logger.Debug(String.Format("file {0}, size is {1}", docXPath, new System.IO.FileInfo(docXPath).Length));
                    }
                    catch (WebException exp)
                    {
                        if (exp.Status == WebExceptionStatus.Timeout)
                        {
                            Logger.Debug("Cannot get docx from conversion server in  5 minutes, retry");
                            client.DownloadFile(url, docXPath);
                        }
                    }

                    return docXPath;
                }

            }
        }

        public string ConvertFile2TempDocX(string filename)
        {
            if (filename.EndsWith("pdf"))
            {
                if (DeclaratorConversionServerUrl != "")
                {
                    try
                    {
                        return DowloadFromConvertedStorage(filename);
                    }
                    catch (Exception exp)
                    {
                        var t = exp.GetType();
                        Logger.Debug("the file cannot be found in conversion server db, try to process this file in place");
                    }
                } 
                else
                {
                    Logger.Error("no url for declarator conversion server specified!");
                }
            }
            string docXPath = filename + ".converted.docx";
            if (filename.EndsWith(".html") || filename.EndsWith(".htm"))
            {
                return ConvertWithSoffice(filename);
            }
            var saveCulture = Thread.CurrentThread.CurrentCulture;
            // Aspose.Words cannot work well, see 7007_10.html in regression tests
            Thread.CurrentThread.CurrentCulture = new System.Globalization.CultureInfo("en-US"); 
            var doc = new Aspose.Words.Document(filename);
            doc.RemoveMacros();
            doc.Save(docXPath, Aspose.Words.SaveFormat.Docx);
            Thread.CurrentThread.CurrentCulture = saveCulture;
            return docXPath;

        }
        public String ConvertWithSoffice(string fileName)
        {
            if (fileName.ToLower().EndsWith("pdf"))
            {
                throw new SmartParserException("libre office cannot convert pdf");
            }
            String outFileName = Path.ChangeExtension(fileName, "docx");
            if (File.Exists(outFileName))
            {
                File.Delete(outFileName);
            };
            var prg = @"C:\Program Files\LibreOffice\program\soffice.exe";
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                prg = "/usr/bin/soffice";
            }
            var outdir = Path.GetDirectoryName(outFileName);
            var args = String.Format(" --headless --writer   --convert-to \"docx:MS Word 2007 XML\"");
            if (outdir != "")
            {
                args += " --outdir " + outdir;
            }

            args += " " + fileName;
            Logger.Debug(prg + " " + args);
            var p = System.Diagnostics.Process.Start(prg, args);
            p.WaitForExit(3 * 60 * 1000); // 3 minutes
            try { p.Kill(true); } catch (InvalidOperationException) { }
            p.Dispose();
            if (!File.Exists(outFileName))
            {
                throw new SmartParserException(String.Format("cannot convert  {0} with soffice", fileName));
            }
            return outFileName;
        }



    }

}