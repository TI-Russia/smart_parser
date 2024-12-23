﻿using System;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using TI.Declarator.JsonSerialization;
using StringHelpers;

namespace TI.Declarator.DeclaratorApiClient
{
    public static class ApiClient
    {
        private static readonly string ReportUnknownEntryUrl = "https://declarator.org/api/unknown_entry/";
        private static readonly string ValidateOutputUrl = "https://declarator.org/api/jsonfile/validate/";
        
        private static HttpClient HttpClient { get; set; }

        private static string Username { get; set; }
        private static string Password { get; set; }

        static ApiClient()
        {
            string[] authLines = File.ReadAllLines("auth.txt");
            Username = authLines[0];
            Password = authLines[1];

            HttpClient = new HttpClient();

            byte[] authBytes = Encoding.ASCII.GetBytes($"{Username}:{Password}");
            string basicAuthInfo = Convert.ToBase64String(authBytes);
            HttpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", basicAuthInfo);
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
