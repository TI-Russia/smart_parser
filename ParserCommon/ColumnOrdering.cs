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

        public void Add(DeclarationField field, int order)
        {
            ColumnOrder.Add(field, order);
        }

        public bool OwnershipTypeInSeparateField
        {
            get
            {
                return ColumnOrder.ContainsKey(DeclarationField.OwnedRealEstateOwnershipType);
            }
        }
    }
}
