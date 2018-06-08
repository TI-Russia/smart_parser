using Smart.Parser.Adapters;
using System.Web.Script.Serialization;

namespace Smart.Parser.Lib
{
    public class JsonWriter
    {
        static JavaScriptSerializer serializer = new JavaScriptSerializer();
        static public void WriteJson(string file, RootObject data)
        {
            string jsonText = serializer.Serialize(data);
            System.IO.File.WriteAllText(file, jsonText);
        }

        static public RootObject ReadJson(string file)
        {
            string jsonText = System.IO.File.ReadAllText(file);
            return serializer.Deserialize<RootObject>(jsonText);
        }
        static public string SerializeCell(Cell cell)
        {
            string jsonText = serializer.Serialize(cell);
            return jsonText;
        }
    };
}