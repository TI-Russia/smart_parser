﻿using StringHelpers;
using SmartParser.Lib;

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
using System.Runtime.InteropServices;
using Adobe.PDFServicesSDK.auth;
using Adobe.PDFServicesSDK.io;
using Adobe.PDFServicesSDK.pdfjobs.jobs;
using Adobe.PDFServicesSDK.pdfjobs.parameters.exportpdf;
using Adobe.PDFServicesSDK.pdfjobs.results;
using Adobe.PDFServicesSDK;
using DocumentFormat.OpenXml.Packaging;
using Smart.Parser.Lib.Adapters.Exceptions;
using DocumentFormat.OpenXml.Wordprocessing;

namespace SmartParser.Lib
{

    public class ConversionServerClient : WebClient
    {
        protected override WebRequest GetWebRequest(Uri uri)
        {
            WebRequest w = base.GetWebRequest(uri);
            w.Timeout = 5 * 60 * 1000; // 5 minutes
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
                    string docXPath = System.IO.Path.GetTempFileName();
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

        public bool TryConvertWithAdobe(string filename)
        {
            string docXPath = filename + ".converted.docx";
            if (File.Exists(docXPath))
            {
                File.Delete(docXPath);
            }
            var clientId = Environment.GetEnvironmentVariable("ADOBE_SERVICES_CLIENT_ID");
            var secret = Environment.GetEnvironmentVariable("ADOBE_SERVICES_CLIENT_SECRET");
            if (clientId == null || secret == null)
            {
                Logger.Info("Cannot convert pdf to docx, no Adobe credentials found. Skip this step.");
                return false;
            }

            try
            {

                var credentials = new ServicePrincipalCredentials(clientId, secret);
                var pdfServices = new PDFServices(credentials);

                using Stream inputStream = File.OpenRead(filename);
                IAsset asset = pdfServices.Upload(inputStream, PDFServicesMediaType.PDF.GetMIMETypeValue());

                var exportPDFParams = ExportPDFParams.ExportPDFParamsBuilder(ExportPDFTargetFormat.DOCX)
                    .WithExportOCRLocale(ExportOCRLocale.RU_RU)
                  .Build();
                var exportPDFJob = new ExportPDFJob(asset, exportPDFParams);

                var location = pdfServices.Submit(exportPDFJob);
                var pdfServicesResponse = pdfServices.GetJobResult<ExportPDFResult>(location, typeof(ExportPDFResult));

                var resultAsset = pdfServicesResponse.Result.Asset;
                var streamAsset = pdfServices.GetContent(resultAsset);

                var outputStream = File.OpenWrite(docXPath);
                streamAsset.Stream.CopyTo(outputStream);
                outputStream.Close();
                return true;
            }
            catch (Exception ex)
            {
                Logger.Error("Cannot convert pdf to docx with Adobe services: " + ex.Message);
                return false;
            }
        }
        public string ConvertFile2TempDocX(string filename)
        {
            string docXPath = filename + ".converted.docx";
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
            if (filename.EndsWith(".html") || filename.EndsWith(".htm"))
            {
                return ConvertWithSoffice(filename);
            }
            var saveCulture = Thread.CurrentThread.CurrentCulture;
            // Aspose.Words cannot work well, see 7007_10.html in regression tests
            Thread.CurrentThread.CurrentCulture = new System.Globalization.CultureInfo("en-US");
            try
            {
                var doc = new Aspose.Words.Document(filename);
                doc.RemoveMacros();
                doc.Save(docXPath, Aspose.Words.SaveFormat.Docx);

                if (!IsDocumentScan(docXPath))
                {
                    if (TryConvertWithAdobe(docXPath))
                    {
                        return docXPath;
                    }
                }

                Thread.CurrentThread.CurrentCulture = saveCulture;
                doc = null;
                System.GC.Collect();
                System.GC.WaitForPendingFinalizers();
                return docXPath;
            }
            catch (Exception exp)
            {
                Thread.CurrentThread.CurrentCulture = saveCulture;
                Logger.Error("Aspose.Words cannot convert the file, most likely due to file corruption. try to use soffice");
                throw new AsposeCorruptedFileException("Aspose.Words cannot convert the file, most likely due to file corruption. try to use soffice");
            }


        }
        public static bool IsDocumentScan(string filePath)
        {
            try
            {
                using (var doc = WordprocessingDocument.Open(filePath, false))
                {
                    var body = doc.MainDocumentPart.Document.Body;

                    // Count text elements in the body
                    int textElements = body.Descendants<Text>().Count(t => !string.IsNullOrWhiteSpace(t.Text));

                    // Include text in headers and footers
                    textElements += doc.MainDocumentPart.HeaderParts
                        .SelectMany(h => h.Header.Descendants<Text>())
                        .Count(t => !string.IsNullOrWhiteSpace(t.Text));

                    textElements += doc.MainDocumentPart.FooterParts
                        .SelectMany(f => f.Footer.Descendants<Text>())
                        .Count(t => !string.IsNullOrWhiteSpace(t.Text));

                    // Define minimum size thresholds (e.g., 300x300 pixels)
                    const int minWidthEmu = 300 * 9525;  // 1 pixel = 9525 EMUs
                    const int minHeightEmu = 300 * 9525;

                    // Function to filter images based on size and visibility
                    bool IsLargeVisibleImage(Drawing drawing)
                    {
                        var extent = drawing.Inline?.Extent ?? drawing.Anchor?.Extent;
                        if (extent == null) return false;

                        var width = extent.Cx;
                        var height = extent.Cy;

                        if (width < minWidthEmu || height < minHeightEmu)
                            return false;

                        // Check visibility
                        DocumentFormat.OpenXml.Drawing.Wordprocessing.DocProperties docProperties = null;

                        if (drawing.Inline != null)
                        {
                            docProperties = drawing.Inline.DocProperties;
                        }
                        else if (drawing.Anchor != null)
                        {
                            docProperties = drawing.Anchor.GetFirstChild<DocumentFormat.OpenXml.Drawing.Wordprocessing.DocProperties>();
                        }

                        if (docProperties != null && docProperties.Hidden != null && docProperties.Hidden)
                            return false;

                        return true;
                    }

                    // Count large, visible images in the body
                    int imageElements = body.Descendants<Drawing>().Count(IsLargeVisibleImage);

                    // Include images in headers and footers
                    imageElements += doc.MainDocumentPart.HeaderParts
                        .SelectMany(h => h.Header.Descendants<Drawing>())
                        .Count(IsLargeVisibleImage);

                    imageElements += doc.MainDocumentPart.FooterParts
                        .SelectMany(f => f.Footer.Descendants<Drawing>())
                        .Count(IsLargeVisibleImage);

                    // Determine if the document is a scan
                    if (textElements == 0 && imageElements > 0)
                    {
                        // No text, but images present
                        return true;
                    }
                    else if (imageElements > 0)
                    {
                        // Calculate the ratio of images to total elements
                        double ratio = (double)imageElements / (textElements + imageElements);
                        if (ratio > 0.8)
                        {
                            return true;
                        }
                    }

                    return false;
                }
            }
            catch (OpenXmlPackageException ex)
            {
                // Handle exceptions (e.g., encrypted or corrupted documents)
                Console.WriteLine($"Error opening document: {ex.Message}");
                return false;
            }
            catch (Exception ex)
            {
                // Handle other exceptions
                Console.WriteLine($"An error occurred: {ex.Message}");
                return false;
            }
        }

        public string ConvertWithSoffice(string fileName)
        {
            if (fileName.ToLower().EndsWith("pdf"))
            {
                throw new SmartParserException("libre office cannot convert pdf");
            }
            string outFileName = System.IO.Path.ChangeExtension(fileName, "docx");
            if (File.Exists(outFileName))
            {
                File.Delete(outFileName);
            };
            var prg = @"C:\Program Files\LibreOffice\program\soffice.exe";
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                prg = "/usr/bin/soffice";
            }
            var outdir = System.IO.Path.GetDirectoryName(outFileName);
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