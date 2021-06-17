using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;

using Newtonsoft.Json;
using Newtonsoft.Json.Schema;
using Newtonsoft.Json.Linq;

using TI.Declarator.ParserCommon;
using Smart.Parser.Lib;

namespace TI.Declarator.JsonSerialization
{
    public class DecimalJsonConverter : JsonConverter
    {
        public DecimalJsonConverter(params Type[] types)
        {
        }

        public override void WriteJson(Newtonsoft.Json.JsonWriter writer, object value, JsonSerializer serializer)
        {
            JToken t = JToken.FromObject(value);

            if (t.Type != JTokenType.Object)
            {
                Decimal d = (Decimal)t;
                writer.WriteValue(d);
            }
            else
            {
                JObject o = (JObject)t;
                o.WriteTo(writer);
            }
        }

        public override object ReadJson(JsonReader reader, Type objectType, object existingValue, JsonSerializer serializer)
        {
            throw new NotImplementedException("Unnecessary because CanRead is false. The type will skip the converter.");
        }

        public override bool CanRead
        {
            get { return false; }
        }

        public override bool CanConvert(Type objectType)
        {
            return objectType == typeof(Decimal);
        }
    }

    public class RealEstateValidator : JsonValidator
    {
        public override void Validate(JToken value, JsonValidatorContext context)
        {
        }
        public override bool CanValidate(JSchema schema)
        {
            return true;
        }
    }

    public enum SmartParserJsonFormatEnum
    {
        Official,
        Disclosures
    }

    public static class DeclarationSerializer
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        private static readonly string SchemaSource = "import-schema-dicts.json";
        private static JSchema Schema;
        private static JSchemaReaderSettings SchemaSettings;
        public static SmartParserJsonFormatEnum SmartParserJsonFormat = SmartParserJsonFormatEnum.Official;

        static DeclarationSerializer()
        {
            SchemaSettings = new JSchemaReaderSettings
            {
                Validators = new List<JsonValidator> { new RealEstateValidator() }
            };
            string executableLocation = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string fullPath = Path.Combine(executableLocation, SchemaSource);
            Schema = JSchema.Parse(File.ReadAllText(fullPath), SchemaSettings);
        }

        public static string Serialize(Declaration declaration)
        {
            string comment = null;
            string result = Serialize(declaration, ref comment);

            return result;
        }

        public static string Serialize(Declaration declaration, bool validate)
        {
            string comments = null;
            string jsonString = Serialize(declaration, ref comments);
            if (validate && comments != null)
            {
                throw new Exception("Could not validate JSON output: " + comments);
            }

            return jsonString;
        }

        public static JObject SerializeDocumentProperties(DeclarationProperties props)
        {
            var jProps = new JObject();
            var title = props.SheetTitle;
            if (title != null)
            {
                title = title.Trim(' ', '\n', '\r');
            }
            AddNotNullProp(jProps, "sheet_title", title);
            jProps.Add(new JProperty("year", props.Year));
            if (SmartParserJsonFormat == SmartParserJsonFormatEnum.Official)
            {
                AddNotNullProp(jProps, "sheet_number", props.SheetNumber);
            }
            AddNotNullProp(jProps, "documentfile_id", props.DocumentFileId);
            AddNotNullProp(jProps, "url", props.DocumentUrl);
            AddNotNullProp(jProps, "archive_file", props.ArchiveFileName);
            if (props.IgnoreThousandMultipler)
            {
                AddNotNullProp(jProps, "ignore_1000_multiplier", "true");
            }
            return jProps;
        }

        public static string Serialize(Declaration declaration, ref string comment, bool validate = true)
        {
            var jServants = new JArray();
            bool storeSheetNumbersInSections = SmartParserJsonFormat == SmartParserJsonFormatEnum.Disclosures && declaration.NotFirstSheetProperties.Count > 0;
            foreach (var servant in declaration.PublicServants)
            {
                jServants.Add(Serialize(servant, declaration.Properties, storeSheetNumbersInSections));
            }

            var jDocumentProp = SerializeDocumentProperties(declaration.Properties);

            var JDeclaration = new JObject(new JProperty("persons", jServants));

            if (SmartParserJsonFormat == SmartParserJsonFormatEnum.Disclosures)
            {
                var jSheetProps = new JArray();
                jSheetProps.Add(jDocumentProp);
                foreach (var p in declaration.NotFirstSheetProperties)
                {
                    jSheetProps.Add(SerializeDocumentProperties(p));
                }
                JDeclaration.Add(new JProperty("document_sheet_props", jSheetProps));
                JDeclaration.Add(new JProperty("json_version", SmartParserJsonFormat.ToString()));
            }
            else
            {
                JDeclaration.Add(new JProperty("document", jDocumentProp));
                if (!ColumnOrdering.SearchForFioColumnOnly)
                {
                    Validate(JDeclaration, out comment);
                }

                if (validate && !comment.IsNullOrWhiteSpace())
                {
                    throw new Exception("JSON output is not valid: " + comment);
                }

            }
            string json = JsonConvert.SerializeObject(JDeclaration, Formatting.Indented, new DecimalJsonConverter());
            json = json.Replace("\r", String.Empty);
            return json;
        }

        private static JObject Serialize(PublicServant servant, DeclarationProperties declarationProperties, bool storeSheetNumbersInSections)
        {
            var jServ = new JObject(
                GetPersonalData(servant),
                GetYear(declarationProperties),
                GetIncomes(servant),
                GetRealEstateProperties(servant),
                GetVehicles(servant));

            AddNotNullProp(jServ, "person_index", servant.Index);
            AddNotNullProp(jServ, "document_position", servant.document_position);
            if (storeSheetNumbersInSections)
            {
                AddNotNullProp(jServ, "sheet_number", servant.sheet_index);
            }
            return jServ;
        }

        private static JProperty GetPersonalData(PublicServant servant)
        {
            JObject personProp = new JObject();
            personProp.Add(new JProperty("name_raw", servant.NameRaw));
            personProp.Add(new JProperty("role", servant.Occupation));
            AddNotNullProp(personProp, "department", servant.Department);

            return new JProperty("person", personProp);
        }

        private static JProperty GetYear(DeclarationProperties declarationInfo)
        {
            if (declarationInfo.Year.HasValue)
            { 
                return new JProperty("year", declarationInfo.Year.Value);
            }
            return new JProperty("year", null);
        }

        private static JProperty GetIncomes(PublicServant servant)
        {
            var jIncomes = new JArray();
            
            if (servant.DeclaredYearlyIncome.HasValue)
            {
                JObject jIncomeProp = new JObject();

                jIncomeProp.Add(new JProperty("size", servant.DeclaredYearlyIncome));
                if (servant.DeclaredYearlyIncomeRaw.Length > 0)
                    jIncomeProp.Add(new JProperty("size_raw", servant.DeclaredYearlyIncomeRaw));
                jIncomeProp.Add(new JProperty("relative", null));

                jIncomes.Add(jIncomeProp);
            }

            foreach (var relative in servant.Relatives)
            {
                var income = relative.DeclaredYearlyIncome;
                if (income.HasValue && income > 0.0m || (relative.DeclaredYearlyIncomeRaw.Length > 0))
                {
                    JObject jIncomeProp = new JObject();

                    jIncomeProp.Add(new JProperty("size", income));
                    if (relative.DeclaredYearlyIncomeRaw.Length > 0)
                        jIncomeProp.Add(new JProperty("size_raw", relative.DeclaredYearlyIncomeRaw));
                    jIncomeProp.Add(new JProperty("relative", GetRelationshipName(relative.RelationType)));
                    AddNotNullProp(jIncomeProp, "relative_index", relative.PersonIndex);

                    jIncomes.Add(jIncomeProp);
                }
            }

            var res = new JProperty("incomes", jIncomes);
            return res;            
        }

        private static void AddNotNullProp(JObject jobj, string prop, object val)
        {
            if (val != null)
            {
                jobj.Add(new JProperty(prop, val));
            }
        }

        private static JObject GetRealEstate(RealEstateProperty prop, string relationshipName = null, int? relative_index = null)
        {
            JObject jRealEstate = new JObject();

            // "text" - "Полная строка наименования недвижимости, которая была в оригинальном документе (сырое значение)",
            jRealEstate.Add(new JProperty("text", prop.Text));
            jRealEstate.Add(new JProperty("square", prop.square));
            jRealEstate.Add(new JProperty("relative", relationshipName));
            AddNotNullProp(jRealEstate, "relative_index", relative_index);
            jRealEstate.Add(new JProperty("own_type_by_column", prop.own_type_by_column));
            AddNotNullProp(jRealEstate, "square_raw", prop.square_raw);
            AddNotNullProp(jRealEstate, "country_raw", prop.country_raw);
            AddNotNullProp(jRealEstate, "type_raw", prop.type_raw);
            AddNotNullProp(jRealEstate, "own_type_raw", prop.own_type_raw);

            return jRealEstate;
        }

        private static JProperty GetRealEstateProperties(PublicServant servant)
        {
            var jRealEstate = new JArray();

            foreach (var prop in servant.RealEstateProperties)
            {
                jRealEstate.Add(GetRealEstate(prop));
            }

            foreach (var rel in servant.Relatives)
            {
                foreach (var prop in rel.RealEstateProperties)
                {
                    var r = GetRealEstate(prop, GetRelationshipName(rel.RelationType), rel.PersonIndex);
                    jRealEstate.Add(r);
                }
            }

            var res = new JProperty("real_estates", jRealEstate);
            return res;
        }

        private static JProperty GetVehicles(PublicServant servant)
        {
            var jVehicles = new JArray();


            foreach (var vehicleInfo in servant.Vehicles)
            {
                JObject jVehicle = new JObject();
                jVehicle.Add(new JProperty("text", vehicleInfo.Text));
                jVehicle.Add(new JProperty("relative", null));
                AddNotNullProp(jVehicle, "type_raw", vehicleInfo.Type);
                AddNotNullProp(jVehicle, "model", vehicleInfo.Model);
                jVehicles.Add(jVehicle);
            }

            foreach (var rel in servant.Relatives)
            {
                foreach (var vehicleInfo in rel.Vehicles)
                {
                    JObject jVehicle = new JObject();
                    jVehicle.Add(new JProperty("text", vehicleInfo.Text));
                    jVehicle.Add(new JProperty("relative", GetRelationshipName(rel.RelationType)));
                    AddNotNullProp(jVehicle, "relative_index", rel.PersonIndex);
                    AddNotNullProp(jVehicle, "type_raw", vehicleInfo.Type);
                    jVehicles.Add(jVehicle);
                }
            }

            var res = new JProperty("vehicles", jVehicles);
            return res;
        }

                      
        private static bool Validate<T>(T jServants, out string message)
        {
            IList<string> comments = new List<string>();

            StringWriter stringWriter = new StringWriter();
            JsonTextWriter writer = new JsonTextWriter(stringWriter);
            JSchemaValidatingWriter validatingWriter = new JSchemaValidatingWriter(writer);
            validatingWriter.Schema = Schema;
            JsonSerializer serializer = new JsonSerializer();

            List<string> messages = new List<string>();
            SchemaValidationEventHandler handler  = 
                delegate (object sender, SchemaValidationEventArgs e) 
                {
                    if (e.Message.StartsWith("Value null is not defined in enum"))
                        return;
                    messages.Add(e.Message);
                };
            validatingWriter.ValidationEventHandler += handler;

            serializer.Serialize(validatingWriter, jServants);


            bool res = messages.Count == 0;
            message = string.Join(" ", messages);
            return res;
        }

        private static string GetRelationshipName(RelationType rt)
        {
            switch (rt)
            {
                case RelationType.Spouse: return "Супруг(а)";
                case RelationType.Child: return "Ребенок";
                case RelationType.Other: return "Иное";
                default: throw new ArgumentOutOfRangeException("rt", $"Unsupported relationship type: {rt.ToString()}");
            }
        }
   
    }
}
