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
        public int? documentfile_id { get; set; }
        public string archive_file { get; set; }
        public int sheet_number { get; set; }
        public string sheet_title { get; set; }
    }
}
