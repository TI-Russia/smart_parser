using System;
using System.Collections.Generic;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class PublicServant : Person
    {
        public string Name { get; set; }

        public string FamilyName{
            get { return Name.Split(new char[] { ' ' })[0]; }
        }

        public string GivenName
        {
            get { return Name.Split(new char[] { ' ' })[1]; }
        }

        public string Patronymic
        {
            get { return Name.Split(new char[] { ' ' })[2]; }
        }

        public string Occupation { get; set; }

        public List<Relative> Relatives = new List<Relative>();

        public XElement ToXml(int personId)
        {
            var res = new XElement("person",
                        new XElement("id", personId),
                        new XElement("name", Name),
                        new XElement("relativeOf", XmlHelpers.Nil()),
                        new XElement("relationType", XmlHelpers.Nil()),
                        new XElement("position", Occupation));

            res.Add(base.ContentsToXml());

            return res;
        }
    }
}
