using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class Declaration
    {
        public IEnumerable<PublicServant> Declarants { get; set; }
        public DeclarationProperties Properties { get; set; }
    }
}
