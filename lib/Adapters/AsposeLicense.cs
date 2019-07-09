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

        public static void SetLicense(string uriString)
        {
            var uri = new Uri(uriString);
            System.IO.Stream stream = null;
            try
            {
                stream = GetContentStream(new Uri(uriString));
            }
            catch
            {
                return;
            }
            Aspose.Cells.License cell_license = new Aspose.Cells.License();
            cell_license.SetLicense(stream);
            stream = GetContentStream(new Uri(uriString));
            Aspose.Words.License word_license = new Aspose.Words.License();
            word_license.SetLicense(stream);
            Licensed = word_license.IsLicensed;
        }
        public static bool Licensed { set; get; } = false;
    }
}
