using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using Smart.Parser.Adapters;
//using System.Web.Script.Serialization;

namespace Smart.Parser.Lib
{
    public class JsonWriter
    {
        static public void WriteJson(string file, object data)
        {

            string jsonText = JsonConvert.SerializeObject(data, new KeyValuePairConverter());

            System.IO.File.WriteAllText(file, jsonText);
        }

        static public string CreateJson(object data)
        {
            return JsonConvert.SerializeObject(data, new KeyValuePairConverter()); ;
        }


        static public T ReadJson<T>(string file)
        {
            string jsonText = System.IO.File.ReadAllText(file);
            return JsonConvert.DeserializeObject<T>(jsonText);
        }

        static public string SerializeCell(Cell cell)
        {
            string jsonText = CreateJson(cell);
            return jsonText;
        }
    };
}