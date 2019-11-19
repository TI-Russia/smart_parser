using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class Declaration
    {
        public List<PublicServant> PublicServants { get; set; } = new List<PublicServant>();
        public DeclarationProperties Properties { get; set; }
        public List<DeclarationSection> Sections { get; set; } = new List<DeclarationSection>();
        public List<DataRowInterface> DataRows;
        public bool MultiplyIncomeIfSpecified = true;
    }

    public class DeclarationSection
    {
        public string Name { get; set; }
        public int Row { get; set; }
    }

}
