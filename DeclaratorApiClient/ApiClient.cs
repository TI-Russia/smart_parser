using System;
using System.IO;
using System.Net;
using System.Net.Http;

using TI.Declarator.JsonSerialization;
using TI.Declarator.ParserCommon;

namespace DeclaratorApiClient
{
    public class ApiClient
    {
        private static readonly string ReportUnknownEntryUrl = "https://declarator.org/api/unknown_entry/";

        private HttpClient HttpClient { get; set; }

        public ApiClient()
        {
            HttpClient = new HttpClient();
        }
        public void ReportUnknownEntry(UnknownEntry ue)
        {
            var reportReq = WebRequest.CreateHttp(ReportUnknownEntryUrl);
            reportReq.ContentType = "application/json";
            reportReq.Method = "POST";

            using (var sw = new StreamWriter(reportReq.GetRequestStream()))
            {
                sw.Write(MiscSerializer.Serialize(ue));
            }

            var httpResponse = reportReq.GetResponse();

            // TODO maybe do something with the response, like error handling
        }
    }
}
