using System;

namespace TI.Declarator.ParserCommon
{
    public class DeclarationProperties
    {
        public string Title { get; set; }
        public ColumnOrdering ColumnOrdering { get; set; }

        public int? Year { get; set; }
        public string MinistryName { get; set; }
        public string SheetName { get; set; }
    }
}
