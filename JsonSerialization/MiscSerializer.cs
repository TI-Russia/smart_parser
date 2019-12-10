using System;
using System.Collections.Generic;

using TI.Declarator.ParserCommon;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace TI.Declarator.JsonSerialization
{
    public static class MiscSerializer
    {
        public static string Serialize(UnknownEntry ue)
        {
            var res = new JObject()
            {
                new JProperty("data", ue.Contents),
                new JProperty("content_type", ue.EntryType),
                new JProperty("file_name", ue.FileName),
                new JProperty("document_file_id", ue.DocumentFileId),
                new JProperty("row", ue.ExcelRowNumber),
                new JProperty("sheet", ue.ExcelSheetNumber),
                new JProperty("page", ue.WordPageNumber)
            };

            return res.ToString();
        }

        public static List<ValidationReport> DeserializeValidationReport(string json)
        {
            return JsonConvert.DeserializeObject<List<ValidationReport>>(json);
        }
    }
}
