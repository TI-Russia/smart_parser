﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace TI.Declarator.ParserCommon
{

    public class UnknownOwnershipTypeException : Exception
    {
        public UnknownOwnershipTypeException(string strType)
            : base("Неизвестный тип владения собственностью:" + strType)
        {
            StrType = strType;
        }

        public string StrType;
    }

    public class UnknownCountryException : Exception
    {
        public UnknownCountryException(string country)
            : base("Неизвестная страна:" + country)
        {
            StrType = country;
        }

        public string StrType;
    }

}
