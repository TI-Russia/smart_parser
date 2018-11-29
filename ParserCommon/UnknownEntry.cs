using System;

namespace TI.Declarator.ParserCommon
{
    public class UnknownEntry
    {
        public string Contents { get; set; }

        public string EntryType { get; set; }

        public string FileName { get; set; }

        public string DocumentFileId { get; set; }

        public int? ExcelRowNumber { get; set; }

        public int? ExcelSheetNumber { get; set; }

        public int? WordPageNumber { get; set; }
    }
}
