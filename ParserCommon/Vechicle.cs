using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class Vechicle
    {
        public Vechicle(string text)
        {
            Text = text;
        }

        public string Text;

        public static implicit operator Vechicle(string v)
        {
            return new Vechicle(v);
        }
    }
}
