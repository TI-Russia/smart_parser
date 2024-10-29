using Azure.AI.FormRecognizer.DocumentAnalysis;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Lib.Adapters.Azure
{
    public class AnalyzeResultDto
    {
        public string ModelId { get; set; }

        public string Content { get; set; }

        public ICollection<DocumentTableCache> Tables { get; set; }
        public ICollection<DocumentParagraphCache> Paragraphs { get; set; }
        public ICollection<DocumentPageCache> Pages { get; set; }
    }

    public class DocumentTableCache
    {
        public int RowCount { get; set; }
        public int ColumnCount { get; set; }
        public List<DocumentTableCellCache> Cells { get; set; }

    }

    public class DocumentTableCellCache
    {
        public DocumentTableCellKind Kind { get; set; }
        public int ColumnSpan { get; set; }
        public int RowIndex { get; set; }
        public int ColumnIndex { get; set; }
        public int RowSpan { get; set; }
        public string Content { get; set; }
    }
    public class DocumentParagraphCache
    {
        public string Content { get; set; }
    }
    public class DocumentPageCache
    {
        public int Unit { get; set; }
        public int PageNumber { get; set; }
        public float Angle { get; set; }
        public float Width { get; set; }
        public float Height { get; set; }
        public ICollection<DocumentWordCache> Words { get; set; }
    }
    public class DocumentWordCache
    {
        public string Content { get; set; }
    }
}
