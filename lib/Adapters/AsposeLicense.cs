using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Adapters
{
    public class AsposeLicense
    {
        static Stream DecryptStream(Stream input)
        {
            RijndaelManaged crypto = new RijndaelManaged()
            {
                Key = Convert.FromBase64String("8/ObWvAv8nj0i1XudnLSsDoC8BlW4y1Xem7a45Dqz08="),
                IV = Convert.FromBase64String("3gwvggWkwQgt7z+/+KMcXg==")
            };
            var decryptor = crypto.CreateDecryptor(crypto.Key, crypto.IV);
            var outputStream = new MemoryStream();
            using (CryptoStream csDecrypt = new CryptoStream(input, decryptor, CryptoStreamMode.Read))
            {
                csDecrypt.CopyTo(outputStream);
            }
            outputStream.Position = 0;
            return outputStream;
        }

        static System.IO.Stream GetContentStream(Uri uri)
        {
            var response = WebRequest.Create(uri).GetResponse();
            var result = response.GetResponseStream();
            if ((!uri.IsFile))
            {
                return DecryptStream(result);
            }
            return result;
        }

        public static System.IO.Stream GetAsposeLicenseStream(string uriString)
        {
            //Console.WriteLine(uriString);
            if (uriString.StartsWith("http"))
            {
                var uri = new Uri(uriString);
                try
                {
                    return  GetContentStream(new Uri(uriString));
                }
                catch
                {
                    return null;
                }
            }
            else
            {
                return DecryptStream(System.IO.File.OpenRead(uriString));
            }

        }
        public static void SetLicense(string uriString)
        {
            Aspose.Cells.License cell_license = new Aspose.Cells.License();
            cell_license.SetLicense(GetAsposeLicenseStream(uriString));

            Aspose.Words.License word_license = new Aspose.Words.License();
            word_license.SetLicense(GetAsposeLicenseStream(uriString));

            //Aspose.Pdf.License pdf_license = new Aspose.Pdf.License();
            //pdf_license.SetLicense(GetAsposeLicenseStream(uriString));

            //Licensed = word_license.IsLicensed;
            Licensed = true;
        }
        public static bool Licensed { set; get; } = false;
    }
}
