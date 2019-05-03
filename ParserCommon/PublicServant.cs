using System;
using System.Collections.Generic;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public class PublicServant : Person
    {
        /// <summary>
        /// Исходное содержимое поля c ФИО чиновника
        /// </summary>
        public string NameRaw { get; set; }

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

    }
}
