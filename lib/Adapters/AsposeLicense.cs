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
            if (!Licensed)
            {
                new Aspose.Cells.License().SetLicense(GetAsposeLicenseStream(uriString));
                new Aspose.Words.License().SetLicense(GetAsposeLicenseStream(uriString));
                Licensed = true;
            }
        }

        public static void SetAsposeLicenseFromEnvironment()
        {
            var envVars = Environment.GetEnvironmentVariables();
            if (envVars.Contains("ASPOSE_LIC"))
            {
                string path = envVars["ASPOSE_LIC"].ToString();
                AsposeLicense.SetLicense(path);
                if (!AsposeLicense.Licensed)
                {
                    throw new Exception("Not valid aspose licence " + path);
                }

            }
        }

        public static bool Licensed { set; get; } = false;
    }
}
