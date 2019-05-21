using System;
using System.Collections.Generic;

using TI.Declarator.ParserCommon;

using Smart.Parser.Adapters;

namespace TI.Declarator.MicrosoftExcel
{
    public class ExcelParser
    {
        private Dictionary<string, RealEstateType> PropertyTypes;

        public static IAdapter GetAdapter(string filename)
        {
            return new MicrosoftExcelAdapter(filename);
        }

        public ExcelParser(Dictionary<string, RealEstateType> propertyTypes)
        {
            this.PropertyTypes = propertyTypes;
        }

        
    }
}
