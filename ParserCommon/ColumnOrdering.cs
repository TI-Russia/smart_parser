using System;
using System.Diagnostics;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class TColumnInfo
    {
        public DeclarationField Field;
        public int BeginColumn;
        public int EndColumn; //initialized in ColumnOrdering::FinishOrderingBuilding 
        public int ColumnPixelStart; //initialized in ColumnOrdering::FinishOrderingBuilding 
        public int ColumnPixelWidth;
        public override string ToString()
        {
            return String.Format("[{0},{1})", BeginColumn,  EndColumn);
        }
    }

    public class ColumnOrdering
    {
        public Dictionary<DeclarationField, TColumnInfo> ColumnOrder = new Dictionary<DeclarationField, TColumnInfo>();
        public List<TColumnInfo> MergedColumnOrder = new List<TColumnInfo>();
        public bool ManyTablesInDocument = false;
        public int? YearFromIncome = null;

        public bool ContainsField(DeclarationField field)
        {
            return ColumnOrder.ContainsKey(field);
        }

        public void Add(TColumnInfo s)
        {
            if (ColumnOrder.ContainsKey(s.Field))
            {
                return;
            }
            ColumnOrder.Add(s.Field, s);
        }
        public void Delete(DeclarationField field)
        {
            ColumnOrder.Remove(field);
        }
        public void FinishOrderingBuilding(int tableIndention)
        {
            MergedColumnOrder.Clear();
            foreach (var x in ColumnOrder.Values)
            {
                MergedColumnOrder.Add(x);
            }
            MergedColumnOrder.Sort((x, y) => x.BeginColumn.CompareTo(y.BeginColumn));
            int sumwidth = tableIndention;
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
        public DeclarationField FindByPixelIntersection(int start, int end, out int maxInterSize)
        {
            DeclarationField field = DeclarationField.None;
            maxInterSize = 0;
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

        public int GetMaxColumnEndIndex()
        {
            Debug.Assert(MergedColumnOrder.Count > 0);
            return MergedColumnOrder[MergedColumnOrder.Count - 1].EndColumn;
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
