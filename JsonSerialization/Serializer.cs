using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

using Newtonsoft.Json;
using Newtonsoft.Json.Schema;
using Newtonsoft.Json.Linq;

using TI.Declarator.ParserCommon;

namespace TI.Declarator.JsonSerialization
{
    public static class DeclarationSerializer
    {
        private static CultureInfo DefaultCulture = CultureInfo.InvariantCulture;
        private static CultureInfo RussianCulture = CultureInfo.CreateSpecificCulture("ru-ru");

        private static readonly string SchemaSource = "import-schema.json";
        private static JSchema Schema;

        static DeclarationSerializer()
        {
            Schema = JSchema.Parse(File.ReadAllText(SchemaSource));
        }

        public static string Serialize(PublicServant servant)
        {
            var jServ = new JObject(
                GetPersonalData(servant),
                GetInstitutiondata(servant),
                GetYear(servant),
                GetIncomes(servant),
                GetRealEstateProperties(servant));
            if (Validate(jServ))
            {
                return jServ.ToString();
            }
            else
            {
                throw new Exception("Could not validate JSON output");
            }
        }

        private static JProperty GetPersonalData(PublicServant servant)
        {
            return new JProperty("person", new JObject(
                                              new JProperty("name", servant.Name),
                                              new JProperty("family_name", servant.FamilyName),
                                              new JProperty("first_name", servant.GivenName),
                                              new JProperty("patronymic_name", servant.Patronymic),
                                              new JProperty("role", servant.Occupation)));
        }

        private static JProperty GetInstitutiondata(PublicServant servant)
        {
            return new JProperty("office", new JObject(
                                            // TODO how to get department name?
                                            new JProperty("name", "Министерство странных походок")));
        }

        private static JProperty GetYear(PublicServant servant)
        {
            // TODO extract year from file name or document title
            return new JProperty("year", 3000);
        }

        private static JProperty GetIncomes(PublicServant servant)
        {
            var jIncomes = new JArray();
            jIncomes.Add(new JObject(
                // TODO should income size really be an integer
                new JProperty("size", (int)servant.DeclaredYearlyIncome),
                new JProperty("relative", null)));

            foreach (var rel in servant.Relatives)
            {
                jIncomes.Add(new JObject(
                new JProperty("size", (int)rel.DeclaredYearlyIncome),
                new JProperty("relative", GetRelationshipName(rel.RelationType))));
            }

            var res = new JProperty("incomes", jIncomes);
            return res;            
        }

        private static JProperty GetRealEstateProperties(PublicServant servant)
        {
            var jRealEstate = new JArray();

            foreach (var prop in servant.RealEstateProperties)
            {
                jRealEstate.Add(new JObject(
                    new JProperty("name", prop.Name),
                    new JProperty("type", prop.PropertyType.ToString()),
                    // TODO should property area really be an integer
                    new JProperty("square", (int)prop.Area),
                    new JProperty("country", prop.Country.ToString()),
                    new JProperty("region", "НЕИЗВЕСТЕН"),
                    new JProperty("own_type", GetOwnershipType(prop)),
                    new JProperty("share_type", GetShareType(prop)),
                    new JProperty("share_amount", GetOwnershipShare(prop)),
                    new JProperty("relative", null)));
            }

            var res = new JProperty("real_estates", jRealEstate);
            return res;
        }

        private static bool Validate(JObject jServant)
        {
            IList<string> comments = new List<string>();
            bool res = jServant.IsValid(Schema, out comments);
            return res;
        }

        private static string GetRelationshipName(RelationType rt)
        {
            switch (rt)
            {
                case RelationType.FemaleSpouse:
                case RelationType.MaleSpouse: return "Супруг(а)";
                case RelationType.Child: return "Ребенок";
                default: throw new ArgumentOutOfRangeException("rt", $"Unsupported relationship type: {rt.ToString()}");
            }
        }

        private static string GetOwnershipType(RealEstateProperty prop)
        {
            if (prop.OwnershipType == OwnershipType.NotAnOwner)
            {
                return "В пользовании";
            }
            else
            {
                return "В собственности";
            }
        }

        private static string GetShareType(RealEstateProperty prop)
        {
            switch(prop.OwnershipType)
            {
                case OwnershipType.Coop: return "Совместная";
                case OwnershipType.Individual: return "Индивидуальная";
                case OwnershipType.NotAnOwner: return "";
                case OwnershipType.Shared: return "Долевая";
                default: throw new ArgumentOutOfRangeException("prop.OwnershipType", $"Unsupported ownership type: {prop.OwnershipType.ToString()}");
            }
        }

        private static decimal? GetOwnershipShare(RealEstateProperty prop)
        {
            string ownedShare = prop.OwnedShare;
            if (prop.OwnershipType == OwnershipType.Shared)
            {
                if (ownedShare.IsNullOrWhiteSpace())
                {
                    return null;
                }
                else if (ownedShare == "½")
                {
                    return 0.5M;
                }
                else if (ownedShare.Contains("/"))
                {
                    var parts = ownedShare.Split(new char[] { '/', ' ' });
                    var num = Decimal.Parse(parts[0]);
                    var den = Decimal.Parse(parts[1]);
                    // Убираем ненужные нули в хвосте и, при необходимости, десятичный разделитель
                    return (num / den);
                }
                else
                {
                    decimal factor = 1.0M;
                    if (ownedShare.EndsWith("%")) { factor = 0.01M; }
                    string shareStr = ownedShare.TrimEnd('%');
                    return Decimal.Parse(shareStr, RussianCulture) * factor;
                }
            }
            else
            {
                return null;
            }
        }
    }
}
