using System;
using System.Collections.Generic;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class PublicServant : Person
    {
        public string NameRaw { get; set; }
        public string Occupation { get; set; }
        public string Department { get; set; }

        public List<Relative> Relatives = new List<Relative>();

    }
}
