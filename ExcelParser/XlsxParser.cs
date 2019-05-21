using System;
using System.IO;
using System.Collections.Generic;

using TI.Declarator.ParserCommon;

using Smart.Parser.Adapters;

namespace TI.Declarator.ExcelParser
{
    public class XlsxParser
    {
        private Dictionary<string, RealEstateType> PropertyTypes;

        public static IAdapter GetAdapter(string filename)
        {
            return new XlsxAdapter(Path.GetFullPath(filename));
        }

        public XlsxParser(Dictionary<string, RealEstateType> propertyTypes)
        {
            this.PropertyTypes = propertyTypes;
        }

        
    }
}
