using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{
    public class Cell
    {
        public virtual bool IsMerged { set; get; } = false;
        public virtual int FirstMergedRow { set; get; } = -1;
        public virtual int MergedRowsCount { set; get; } = -1;
        public virtual bool IsHeader { set; get; } = false;
        public virtual bool IsEmpty { set; get; } = true;
        public virtual string BackgroundColor { set; get; }
        public virtual string ForegroundColor { set; get; }

        public virtual string Text { set; get; } = "";
    };

    public interface IAdapter
    {
//        Cell GetCell(string cellNum);
        Cell GetCell(int row, int column);

        Cell GetDeclarationField(int row, DeclarationField field);

        int GetRowsCount();
        int GetColsCount();
        void SetColumnOrdering(ColumnOrdering columnOrdering);

    }
}
