using System;
using System.Xml.Linq;

namespace TI.Declarator.ParserCommon
{
    public static class XmlHelpers
    {
        private static XNamespace xsi = XNamespace.Get("http://www.w3.org/2001/XMLSchema-instance");
        public static XNamespace Xsi
        {
            get { return xsi; }
        }

        public static XAttribute Nil()
        {
            return new XAttribute(new XAttribute(xsi + "nil", "true"));
        }
    }
}
