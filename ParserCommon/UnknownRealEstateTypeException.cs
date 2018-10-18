using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace TI.Declarator.ParserCommon
{
    public class UnknownRealEstateTypeException : Exception
    {
        public UnknownRealEstateTypeException(string strType) 
            : base("Неизвестный тип недвижимости:" + strType)
        {
            StrType = strType;
        }

        public string StrType;
    }
}
