using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class Vehicle
    {
        public Vehicle(string text, string type = null)
        {
            Text = text;
            Type = type;
        }

        public string Text;
        public string Type;

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
