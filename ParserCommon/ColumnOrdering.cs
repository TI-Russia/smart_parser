using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public class ColumnOrdering
    {
        private Dictionary<Field, int> ColumnOrder = new Dictionary<Field, int>();

        public int this[Field field]
        {
            get
            {
                return ColumnOrder[field];
            }
        }

        public void Add(Field field, int order)
        {
            ColumnOrder.Add(field, order);
        }
    }
}
