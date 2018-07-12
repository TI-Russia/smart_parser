using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{
    public class AdapterBase
    {
        public void SetColumnOrdering(ColumnOrdering columnOrdering)
        {
            this.columnOrdering = columnOrdering;
        }

        protected int Field2Col(DeclarationField field)
        {
            int index = -1;
            if (!columnOrdering.ColumnOrder.TryGetValue(field, out index))
            {
                //return -1;
                throw new SystemException("Field " + field.ToString() + " not found");
            }
            return index;
        }

        private ColumnOrdering columnOrdering = null;
    }
}
