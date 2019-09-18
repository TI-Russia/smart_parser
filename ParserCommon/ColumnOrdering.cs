using System;
using System.Collections.Generic;
using System.Collections.Specialized;

namespace TI.Declarator.ParserCommon
{
    public class TColumnInfo
    {
        public DeclarationField Field;
        public int BeginColumn;
        public int EndColumn;
        public int ColumnPixelStart;
        public int ColumnPixelWidth;
    }
    public class ColumnOrdering
    {
        public Dictionary<DeclarationField, TColumnInfo> ColumnOrder = new Dictionary<DeclarationField, TColumnInfo>();
        public List<TColumnInfo> MergedColumnOrder = new List<TColumnInfo>();
        public bool ContainsField(DeclarationField field)
        {
            return ColumnOrder.ContainsKey(field);
        }

        public void Add(DeclarationField field, int beginColumn, int columnWidth)
        {
            if (ColumnOrder.ContainsKey(field))
            {
                return;
            }
            TColumnInfo s = new TColumnInfo();
            s.BeginColumn = beginColumn;
            s.EndColumn = beginColumn + 1;
            s.ColumnPixelWidth = columnWidth;
            s.Field = field;
            ColumnOrder.Add(field, s);
        }
        public void Delete(DeclarationField field)
        {
            ColumnOrder.Remove(field);
        }
        public void FinishOrderingBuilding()
        {
            MergedColumnOrder.Clear();
            foreach (var x in ColumnOrder.Values)
            {
                MergedColumnOrder.Add(x);
            }
            MergedColumnOrder.Sort((x, y) => x.BeginColumn.CompareTo(y.BeginColumn));
            int sumwidth = 0;
            foreach (var x in MergedColumnOrder)
            {
                x.ColumnPixelStart = sumwidth;
                sumwidth += x.ColumnPixelWidth;
            }
        }
        public static int PeriodIntersection(int start1, int end1, int start2, int end2)
        {
            if (start1 <= end2 && start2 <= end1) // overlap exists
            {
                return Math.Min(end1, end2) - Math.Max(start1, start2);
            }
            return 0;
        }
        public DeclarationField FindByPixelIntersection(int start, int end)
        {
            DeclarationField field = DeclarationField.None;
            int maxInterSize = 0;
            foreach (var x in ColumnOrder)
            {
                int interSize = PeriodIntersection(start, end, x.Value.ColumnPixelStart, x.Value.ColumnPixelStart + x.Value.ColumnPixelWidth);
                if (interSize > maxInterSize)
                {
                    maxInterSize = interSize;
                    field = x.Key; 
                }
            }
            return field;
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
