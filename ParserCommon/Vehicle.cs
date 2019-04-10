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
        public Vehicle(string text)
        {
            Text = text;
        }

        public string Text;

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
