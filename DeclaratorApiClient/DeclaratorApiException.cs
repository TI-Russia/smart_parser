using System;

using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;

namespace TI.Declarator.DeclaratorApiClient
{
    class DeclaratorApiException : Exception
    {
        public HttpResponseMessage ResponseMessage { get; private set; }

        public DeclaratorApiException(HttpResponseMessage response, string msg)
            : base(msg + $" status: {response.ReasonPhrase}")
        {
            this.ResponseMessage = response;
        }
    }
}
