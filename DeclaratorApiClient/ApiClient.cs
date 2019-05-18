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
    }
}
