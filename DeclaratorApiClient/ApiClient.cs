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

        private static HttpClient HttpClient { get; set; }

        private static readonly string Username = "username";
        private static readonly string Password = "password";

        static ApiClient()
        {
            HttpClient = new HttpClient();

            byte[] authBytes = Encoding.ASCII.GetBytes($"{Username}:{Password}");
            string basicAuthInfo = Convert.ToBase64String(authBytes);
            HttpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", basicAuthInfo);
        }
        public static void ReportUnknownEntry(UnknownEntry ue)
        {
            var reportReq = WebRequest.CreateHttp(ReportUnknownEntryUrl);
            string jsonContents = MiscSerializer.Serialize(ue);
            var contents = new StringContent(jsonContents, Encoding.UTF8, "application/json");            
            var httpResponse = HttpClient.PostAsync(ReportUnknownEntryUrl, contents).Result;

            if (!httpResponse.IsSuccessStatusCode)
            {
                throw new DeclaratorApiException(httpResponse, "Could not report unknown entry to Declarator API");
            }            
        }
    }
}
