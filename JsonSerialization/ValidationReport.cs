using System;
using System.Collections.Generic;

using Newtonsoft.Json;

namespace TI.Declarator.JsonSerialization
{
    public class ValidationReport
    {
        [JsonProperty("errors")]
        public ValidationErrors Errors { get; set; }
    }

    public class ValidationErrors
    {
        [JsonProperty("person")]
        public PersonErrors PersonErrors { get; set; }

        [JsonProperty("real_estates")]
        public List<RealEstateError> RealEstateErrors { get; set; }

        [JsonProperty("incomes")]
        public List<IncomeError> IncomeErrors { get; set; }
    }

    public class PersonErrors
    {
        [JsonProperty("role")]
        public List<string> RoleErrors { get; set; }
    }

    public class RealEstateError
    {
        [JsonProperty("share_type")]
        public List<string> ShareTypeErrors { get; set; }
    }

    public class IncomeError
    {
        [JsonProperty("size")]
        public List<string> SizeErrors { get; set; }
    }
}
