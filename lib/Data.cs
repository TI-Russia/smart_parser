namespace Smart.Parser.Lib
{
    public class RootObject
    {
        public Person person { get; set; }
        public Office office { get; set; }
        public string party { get; set; }
        public int year { get; set; }
        public Document document { get; set; }
        public Income[] incomes { get; set; }
        public Real_Estates[] real_estates { get; set; }
        public Vehicle[] vehicles { get; set; }
        public object[] spendings { get; set; }
    }

    public class Person
    {
        public string name { get; set; }
        public string family_name { get; set; }
        public string given_name { get; set; }
        public string patronymic_name { get; set; }
        public string role { get; set; }
    }

    public class Office
    {
        public string name { get; set; }
        public string url { get; set; }
        public string type { get; set; }
        public string region { get; set; }
    }

    public class Document
    {
        public string type { get; set; }
        public string name { get; set; }
        public string url { get; set; }
        public string page_url { get; set; }
    }

    public class Income
    {
        public float size { get; set; }
        public string relative { get; set; }
    }

    public class Real_Estates
    {
        public string name { get; set; }
        public string type { get; set; }
        public float square { get; set; }
        public string country { get; set; }
        public string region { get; set; }
        public string own_type { get; set; }
        public string share_type { get; set; }
        public float? share_amount { get; set; }
        public string relative { get; set; }
        public string comment { get; set; }
    }

    public class Vehicle
    {
        public string full_name { get; set; }
        public string type { get; set; }
        public string brand { get; set; }
        public string model { get; set; }
        public object manufacture_year { get; set; }
        public object relative { get; set; }
    }

}