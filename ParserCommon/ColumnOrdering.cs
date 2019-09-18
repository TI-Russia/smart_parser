using System.Collections.Generic;
using System.Collections.Specialized;

namespace TI.Declarator.ParserCommon
{
    public class TColumnSpan
    {
        public int BeginColumn;
        public int EndColumn;
    }
    public class ColumnOrdering
    {
        public Dictionary<DeclarationField, TColumnSpan> ColumnOrder = new Dictionary<DeclarationField, TColumnSpan>();
        public bool ContainsField(DeclarationField field)
        {
            return ColumnOrder.ContainsKey(field);
        }

        public void Add(DeclarationField field, int beginColumn)
        {
            if (ColumnOrder.ContainsKey(field))
            {
                return;
            }
            TColumnSpan s = new TColumnSpan();
            s.BeginColumn = beginColumn;
            s.EndColumn = beginColumn + 1;
            ColumnOrder.Add(field, s);
        }
        public void Delete(DeclarationField field)
        {
            ColumnOrder.Remove(field);
        }
        public void FinishOrderingBuilding()
        {
        }

        public void InitHeaderEndColumns(int lastColumn)
        {
            foreach (var i in ColumnOrder) {
                int start = i.Value.BeginColumn;
                int end = lastColumn;
                foreach (var k in ColumnOrder)
                {
                    int newEnd = k.Value.BeginColumn;
                    if (newEnd > start)
                    {
                        if (newEnd < end )
                        {
                            end = newEnd;
                        };
                    }
                }
                i.Value.EndColumn = end;
            }
        }

        public bool OwnershipTypeInSeparateField
        {
            get
            {
                return ColumnOrder.ContainsKey(DeclarationField.OwnedRealEstateOwnershipType);
            }
        }
        public int FirstDataRow { get; set; } = 1;
        public string Title { get; set; }
        public string MinistryName { get; set; }
        public string Section { get; set; }
        public int? Year { get; set; }
        public int? HeaderBegin { get; set; }
        public int? HeaderEnd { get; set; }
        public int GetPossibleHeaderBegin()
        {
            return HeaderBegin ?? 0;
        }
        public int GetPossibleHeaderEnd()
        {
            return HeaderEnd ?? GetPossibleHeaderBegin() + 2;
        }

    }
}
