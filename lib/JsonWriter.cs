using System.Web.Script.Serialization;

namespace Smart.Parser.Lib
{
    public class JsonWriter
    {
        static public void WriteJson(string file, RootObject data)
        {
            var serializer = new JavaScriptSerializer();
            string jsonText = serializer.Serialize(data);
            System.IO.File.WriteAllText(file, jsonText);
        }

        static public RootObject ReadJson(string file)
        {
            var serializer = new JavaScriptSerializer();
            string jsonText = System.IO.File.ReadAllText(file);
            return serializer.Deserialize<RootObject>(jsonText);
        }

    };

}