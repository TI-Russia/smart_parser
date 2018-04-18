using System;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class Relative : Person
    {
        public RelationType RelationType { get; set; }

        public XElement ToXml(int personId, int publicServantId)
        {
            var res = new XElement("person",
                        new XElement("id", personId),
                        new XElement("name", XmlHelpers.Nil()),
                        new XElement("relativeOf", publicServantId),
                        new XElement("relationType", (int)RelationType),
                        new XElement("position", XmlHelpers.Nil()));

            res.Add(base.ContentsToXml());

            return res;
        }
    }
}
