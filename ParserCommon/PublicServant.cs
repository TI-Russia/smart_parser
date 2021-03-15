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

        public int? Index { get; set; }

        public void AddRelative(Relative relative)
        {
            relative.PersonIndex = relatives.Count + 1;
            relatives.Add(relative);
        }

        public IEnumerable<Relative> Relatives
        {
            get
            {
                return relatives;
            }
        }

        List<Relative> relatives = new List<Relative>();
        public override int? PersonIndex { get { return null; } }
        public ColumnOrdering Ordering;
    }
}
