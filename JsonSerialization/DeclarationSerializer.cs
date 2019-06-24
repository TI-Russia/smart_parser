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
                //int count = BitConverter.GetBytes(decimal.GetBits(d)[3])[2];
                //string s = d.ToString();
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

    public static class DeclarationSerializer
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        private static readonly string SchemaSource = "import-schema-dicts.json";
        private static JSchema Schema;
        private static JSchemaReaderSettings SchemaSettings;

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

        public static JProperty SerializeDocument(Declaration declaration)
        {
            var jDocument = new JObject();
            AddNotNullProp(jDocument, "sheet_title", declaration.Properties.Title);
            jDocument.Add(new JProperty("year", declaration.Properties.Year));
            AddNotNullProp(jDocument, "sheet_number", declaration.Properties.sheet_number);
            AddNotNullProp(jDocument, "documentfile_id", declaration.Properties.documentfile_id);
            AddNotNullProp(jDocument, "archive_file", declaration.Properties.archive_file);

            return new JProperty("document", jDocument);
        }

        public static string Serialize(Declaration declaration, ref string comment, bool validate = true)
        {
            var jServants = new JArray();
            foreach (var servWithInd in declaration.PublicServants.Select((serv, ind) => new { serv, ind }))
            {
                jServants.Add(Serialize(servWithInd.serv, servWithInd.ind, declaration.Properties));
            }

            var jPersonsProp = new JProperty("persons", jServants);
            var jDocument  = new JObject();
            var jDocumentProp = SerializeDocument(declaration);
            
            var JDeclaration = new JObject(jPersonsProp, jDocumentProp);
            
            Validate(JDeclaration, out comment);

            if (validate && !comment.IsNullOrWhiteSpace())
            {
                throw new Exception("JSON output is not valid: " + comment);
            }

            string json = JsonConvert.SerializeObject(JDeclaration, Formatting.Indented, new DecimalJsonConverter());
            return json;
        }

        private static JObject Serialize(PublicServant servant, int ind, DeclarationProperties declarationProperties)
        {
            var jServ = new JObject(
                GetPersonalData(servant),
                //GetInstitutiondata(servant),
                GetYear(declarationProperties),
                GetIncomes(servant),
                GetRealEstateProperties(servant),
                GetVehicles(servant),
                GetPersonIndexProp(ind + 1));
            return jServ;
        }

        private static JProperty GetPersonalData(PublicServant servant)
        {
            JObject personProp = new JObject();
            personProp.Add(new JProperty("name", servant.Name));
            personProp.Add(new JProperty("name_raw", servant.NameRaw));
            personProp.Add(new JProperty("role", servant.Occupation));
            AddNotNullProp(personProp, "department", servant.Department);

            return new JProperty("person", personProp);
        }

        private static JProperty GetInstitutiondata(PublicServant servant)
        {
            return new JProperty("office", new JObject(
                                            // TODO how to get department name?
                                            new JProperty("name", "Министерство странных походок")));
        }

        private static JProperty GetYear(DeclarationProperties declarationInfo)
        {
            // TODO extract year from file name or document title
            if (declarationInfo.Year.HasValue)
            { 
                return new JProperty("year", declarationInfo.Year.Value);
            }
            {
                throw new Exception("Error serializing declaration: year is missing");
            }
        }

        private static JProperty GetIncomes(PublicServant servant)
        {
            var jIncomes = new JArray();
            
            if (servant.DeclaredYearlyIncome.HasValue)
            { 
                jIncomes.Add(new JObject(
                    new JProperty("size", servant.DeclaredYearlyIncome),
                    new JProperty("relative", null)));
            }

            foreach (var rel in servant.Relatives)
            {
                var income = rel.DeclaredYearlyIncome;
                if (income.HasValue && income > 0.0m)
                {
                    jIncomes.Add(new JObject(
                    new JProperty("size", income),
                    new JProperty("relative", GetRelationshipName(rel.RelationType))));
                }
            }

            var res = new JProperty("incomes", jIncomes);
            return res;            
        }

        private static JProperty GetPersonIndexProp(int index)
        {
            return new JProperty("person_index", index);
        }

        private static void AddNotNullProp(JObject jobj, string prop, object val)
        {
            if (val != null)
            {
                jobj.Add(new JProperty(prop, val));
            }
        }

        private static JObject GetRealEstate(RealEstateProperty prop, string relationshipName = null)
        {
            JObject jRealEstate = new JObject();

            // "text" - "Полная строка наименования недвижимости, которая была в оригинальном документе (сырое значение)",
            //jRealEstate.Add(new JProperty("name", prop.Name));
            jRealEstate.Add(new JProperty("text", prop.Text));
            // "type_raw" - "Тип недвижимости (сырой текст из соответствующей ячейки документа)",
            jRealEstate.Add(new JProperty("type", GetPropertyType(prop.PropertyType)));
            jRealEstate.Add(new JProperty("square", prop.Square));
            bool isCountryRecognized = prop.Country != Country.None && prop.Country != Country.Error;
            if (isCountryRecognized)
            {
                jRealEstate.Add(new JProperty("country", prop.CountryStr ?? GetCountry(prop)));
            }
            else
            {
                jRealEstate.Add(new JProperty("country", GetCountry(prop)));
            }
            jRealEstate.Add(new JProperty("region", null));
            // "own_type_raw"
            jRealEstate.Add(new JProperty("own_type", GetOwnershipType(prop)));
            // "share_type_raw"
            //new JProperty("share_type", GetShareType(prop)),
            jRealEstate.Add(new JProperty("share_amount", GetOwnershipShare(prop)));

            jRealEstate.Add(new JProperty("relative", relationshipName));

            AddNotNullProp(jRealEstate, "square_raw", prop.square_raw);
            AddNotNullProp(jRealEstate, "share_amount_raw", prop.share_amount_raw);
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
                    jRealEstate.Add(GetRealEstate(prop, GetRelationshipName(rel.RelationType)));
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
                AddNotNullProp(jVehicle, "type", vehicleInfo.Type);
                jVehicles.Add(jVehicle);
            }

            foreach (var rel in servant.Relatives)
            {
                foreach (var vehicleInfo in rel.Vehicles)
                {
                    JObject jVehicle = new JObject();
                    jVehicle.Add(new JProperty("text", vehicleInfo.Text));
                    jVehicle.Add(new JProperty("relative", GetRelationshipName(rel.RelationType)));
                    AddNotNullProp(jVehicle, "type", vehicleInfo.Type);
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


            //bool res = jServants.IsValid(Schema, out comments);
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
                default: throw new ArgumentOutOfRangeException("rt", $"Unsupported relationship type: {rt.ToString()}");
            }
        }
        private static string GetSquareString(RealEstateProperty prop)
        {
            return prop.Square == null ? "null" : prop.Square.Value.ToString("#.##");
        }

        private static string GetPropertyType(RealEstateType propertyType)
        {
            if (propertyType == RealEstateType.None)
            {
                return null;
            }
            return DeclaratorApiPatterns.RealEstateTypeToString(propertyType);
            /*
            switch (propertyType)
            {                
                case RealEstateType.Apartment:
                case RealEstateType.Rooms: return "Квартира";
                case RealEstateType.Room: return "Квартира";
                case RealEstateType.Garage: return "Гараж";
                case RealEstateType.Dacha:
                case RealEstateType.DachaHouse: return "Дача";
                case RealEstateType.House: return "Жилой дом";
                case RealEstateType.HabitableHouse: return "Жилой дом";
                //case RealEstateType.GardenPlot:
                case RealEstateType.PlotOfLand: return "Земельный участок";
                case RealEstateType.Building:
                case RealEstateType.HabitableSpace:
                case RealEstateType.ParkingSpace:
                case RealEstateType.Other: return "Иное";
                default: throw new ArgumentOutOfRangeException("prop.PropertyType", $"Unsupported real estate type: {prop.PropertyType.ToString()}");
            }
            */
        }

        private static string GetCountry(RealEstateProperty prop)
        {
            switch (prop.Country)
            {
                case Country.Error: return null;
                case Country.None: return null;
                case Country.France: return "Франция";
                case Country.Russia: return "Россия";
                case Country.Ukraine: return "Украина";
                case Country.Kazakhstan: return "Казахстан";
                case Country.Bulgaria: return "Болгария";
                case Country.Belarus: return "Беларусь";
                case Country.Georgia: return "Грузия";
                case Country.Lithuania: return "Литва";
                case Country.Portugal: return "Португалия";
                case Country.Usa: return "США";
                case Country.Thailand: return "Тайланд";
                case Country.Hungary: return "Венгрия";
                case Country.Latvia: return "Латвия";
                case Country.Uzbekistan: return "Узбекистан";
                case Country.Armenia: return "Армения";
                case Country.Turkey: return "Турция";
                case Country.Spain: return "Испания";
                case Country.Estonia: return "Эстония";
                case Country.Mongolia: return "Монголия";
                case Country.Tajikistan: return "Таджикистан";
                case Country.CzechRepublic: return "Чехия";
                case Country.Kyrgyzstan: return "Киргизия";
                case Country.Finland: return "Финляндия";
                case Country.Turkmenistan: return "Туркмения";
                case Country.Montenegro: return "Черногория";
                case Country.Mexico: return "Мексика";
                case Country.Abkhazia: return "Абхазия";
                case Country.SouthOssetia: return "Южная Осетия";
                case Country.UnitedKingdom: return "Великобритания";

                default:
                    Console.Write($"Invalid country name: {prop.Country.ToString()}");
                    return prop.Country.ToString();
                    //throw new ArgumentOutOfRangeException("prop.Country", $"Invalid country name: {prop.Country.ToString()}");
            }
        }

        private static string GetOwnershipType(RealEstateProperty prop)
        {
            return prop.OwnershipType.ToJsonString();
        }

        private static string GetShareType(RealEstateProperty prop)
        {
            return prop.OwnershipType.ToJsonString();
        }

        private static decimal? GetOwnershipShare(RealEstateProperty prop)
        {
            string ownedShare = prop.OwnedShare;
            //if (prop.OwnershipType == OwnershipType.Shared)
            {
                if (ownedShare.IsNullOrWhiteSpace())
                {
                    return null;
                }
                else if (ownedShare == "½")
                {
                    return 0.5M;
                }
                else if (ownedShare == "¼")
                {
                    return 0.25M;
                }
                else if (ownedShare.Contains("/"))
                {
                    var parts = ownedShare.Split(new char[] { '/', ' ' });
                    var num = Decimal.Parse(parts[0]);
                    var den = Decimal.Parse(parts[1]);
                    // Убираем ненужные нули в хвосте и, при необходимости, десятичный разделитель

                    if (den == 0)
                        return null;
                    return (num / den);
                }
                else
                {
                    decimal factor = 1.0M;
                    if (ownedShare.EndsWith("%")) { factor = 0.01M; }
                    string shareStr = ownedShare.TrimEnd('%');
                    Decimal value;
                    if (!Decimal.TryParse(shareStr, NumberStyles.Any, RussianCulture, out value))
                    {
                        // TBD: Log error
                        Console.Write($"can't parse ownedShare: {ownedShare}");
                        return 0;
                    }

                    return value * factor;
                }
            }
            //else
            //{
            //    return null;
            //}
        }
    }
}
