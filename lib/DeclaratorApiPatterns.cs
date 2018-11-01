using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace Smart.Parser.Lib
{
    public class Rootobject
    {
        public int count { get; set; }
        public string next { get; set; }
        public object previous { get; set; }
        public Result[] results { get; set; }
    }

    public class Result
    {
        public string data { get; set; }
        public int id { get; set; }
        public bool is_case { get; set; }
        public bool is_regex { get; set; }
        public string type { get; set; }
        public string value { get; set; }
    }


    public class DeclaratorApiPatterns
    {
        static string GetResourceText()
        {
            string result = null;
            var currentAssembly = Assembly.GetExecutingAssembly();
            using (var stream = currentAssembly.GetManifestResourceStream("Parser.Lib.Resources.patterns.json"))
            using (var reader = new StreamReader(stream))
            {
                result = reader.ReadToEnd();
            }
            return result;
        }

        static Rootobject patterns = null;
        static Rootobject Patterns
        {
            get
            {
                if (patterns == null)
                    patterns = JsonConvert.DeserializeObject<Rootobject>(GetResourceText());
                return patterns;
            }
        }
        public static string GetValue(string text, string type)
        {
            foreach (Result pattern in Patterns.results.Where(result => result.type == type))
            {
                if (pattern.is_regex)
                {
                    if (Regex.Match(text, pattern.data).Success)
                        return pattern.value.Trim();
                }
                else if (pattern.data == text)
                {
                    return pattern.value.Trim();
                }
            }

            

            return null;
        }

    }
}

