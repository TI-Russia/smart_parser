using System;
using System.Collections.Generic;

using Newtonsoft.Json;

namespace TI.Declarator.JsonSerialization
{
    public static class MiscSerializer
    {
        public static List<ValidationReport> DeserializeValidationReport(string json)
        {
            return JsonConvert.DeserializeObject<List<ValidationReport>>(json);
        }
    }
}
