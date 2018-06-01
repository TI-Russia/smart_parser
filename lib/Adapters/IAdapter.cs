﻿using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Adapters
{
    public class Cell
    {
        public virtual bool IsHeader { set; get; }
        public virtual bool IsEmpty { set; get; }
        public virtual string BackgroundColor { set; get; }
        public virtual string ForegroundColor { set; get; }

        public virtual string Text { set; get; }
    };

    public interface IAdapter
    {
        Cell GetCell(string cellNum);
        Cell GetCell(int row, int column);
        int GetRowsCount();
    }
}
