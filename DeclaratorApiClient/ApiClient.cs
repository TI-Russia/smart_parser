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

        private static readonly string Username = "david_parsers";
        private static readonly string Password = "2OoHdAU9";

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
            
            var httpResponseTask = HttpClient.PostAsJsonAsync(ReportUnknownEntryUrl, jsonContents);
            httpResponseTask.Wait();
            var httpResponse = httpResponseTask.Result;

            // TODO maybe do something with the response, like error handling
        }
    }
}
