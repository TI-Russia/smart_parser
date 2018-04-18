using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class ColumnOrdering
    {
        private Dictionary<Field, short> ColumnOrder = new Dictionary<Field, short>();

        public short this[Field field]
        {
            get
            {
                return ColumnOrder[field];
            }
        }

        public void Add(Field field, short order)
        {
            ColumnOrder.Add(field, order);
        }
    }
}
