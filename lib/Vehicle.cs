using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;

namespace SmartParser.Lib
{
    public class Vehicle
    {
        public Vehicle(string text, string type = null, string model = null)
        {
            Text = text;
            Type = type;
            Model = model;
        }

        public string Text;
        public string Type;
        public string Model;

        public static implicit operator Vehicle(string v)
        {
            return new Vehicle(v);
        }
        public static implicit operator string(Vehicle v)
        {
            return v.Text;
        }
    }
}
