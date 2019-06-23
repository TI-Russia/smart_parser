using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Formatting;
using System.Net.Http.Headers;
using System.Text;
using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;

namespace TI.Declarator.DeclaratorApiClient
{
    public static class ApiClient
    {
        private static readonly string ReportUnknownEntryUrl = "https://declarator.org/api/unknown_entry/";
        private static readonly string ValidateOutputUrl = "https://declarator.org/api/jsonfile/validate/";
        private static readonly string PatternsUrl = "https://declarator.org/api/patterns";
        
        private static HttpClient HttpClient { get; set; }

        private static readonly string Username = "david_parsers";
        private static readonly string Password = "vMrkq002";

        static ApiClient()
        {
            HttpClient = new HttpClient();

            byte[] authBytes = Encoding.ASCII.GetBytes($"{Username}:{Password}");
            string basicAuthInfo = Convert.ToBase64String(authBytes);
            HttpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", basicAuthInfo);
        }
        public static void ReportUnknownEntry(UnknownEntry ue)
        {
            string jsonContents = MiscSerializer.Serialize(ue);
            var contents = new StringContent(jsonContents, Encoding.UTF8, "application/json");            
            var httpResponse = HttpClient.PostAsync(ReportUnknownEntryUrl, contents).Result;

            if (!httpResponse.IsSuccessStatusCode)
            {
                throw new DeclaratorApiException(httpResponse, "Could not report unknown entry to Declarator API");
            }
        }

        public static string ValidateParserOutput(string jsonOutput)
        {
            var contents = new StringContent(jsonOutput, Encoding.UTF8, "application/json");
            var httpResponse = HttpClient.PostAsync(ValidateOutputUrl, contents).Result;

            if (!httpResponse.IsSuccessStatusCode)
            {
                throw new DeclaratorApiException(httpResponse, "Could not validate parser output");
            }

            return httpResponse.Content.ReadAsStringAsync().Result;
        }
        public static string DownloadPatterns()
        {
            // sokirko: does not work because of Authorization problems, use download.py
            dynamic result = null;
            var url = PatternsUrl;
            while (true) {
                var contents = new StringContent("");
                var httpResponse = HttpClient.PostAsync(url, contents).Result;

                if (!httpResponse.IsSuccessStatusCode)
                {
                    throw new DeclaratorApiException(httpResponse, "Could not validate parser output");
                }
                var s = httpResponse.Content.ReadAsStringAsync().Result;
                dynamic patterns = Newtonsoft.Json.JsonConvert.DeserializeObject(s);
                if (result == null)
                {
                    result = patterns;
                }
                else
                {
                    result.results += patterns.results;
                }
                if (patterns.next == "") break;
                url = patterns.next;
            }
            return Newtonsoft.Json.JsonConvert.DeserializeObject(result);
        }
    }
}
