using System;

namespace SmartParser.Lib
{
    public class DeclarationProperties
    {
        public string SheetTitle { get; set; }
        public int? Year { get; set; }
        public int? DocumentFileId { get; set; }
        public string? DocumentUrl { get; set; }
        public string ArchiveFileName { get; set; }
        public int? SheetNumber { get; set; }

        public bool IgnoreThousandMultipler = false;
    }
}
