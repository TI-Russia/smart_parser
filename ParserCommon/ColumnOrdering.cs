using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class ColumnOrdering
    {
        public Dictionary<DeclarationField, int> ColumnOrder = new Dictionary<DeclarationField, int>();

        public int? this[DeclarationField field]
        {
            get
            {
                if (ColumnOrder.ContainsKey(field))
                {
                    return ColumnOrder[field];
                }
                else
                {
                    return null;
                }
            }
        }

        public bool ContainsField(DeclarationField field)
        {
            return ColumnOrder.ContainsKey(field);
        }

        public void Add(DeclarationField field, int order)
        {
            if (ColumnOrder.ContainsKey(field))
            {
                return;
            }
            ColumnOrder.Add(field, order);
        }

        public bool OwnershipTypeInSeparateField
        {
            get
            {
                return ColumnOrder.ContainsKey(DeclarationField.OwnedRealEstateOwnershipType);
            }
        }
        public int FirstDataRow { get; set; } = 1;
    }
}
