using System;
using System.Xml.Linq;

namespace SmartParser.Lib
{
    public class Relative : Person
    {
        public RelationType RelationType { get; set; }
        public override int? PersonIndex { get; set; }
    }
}
