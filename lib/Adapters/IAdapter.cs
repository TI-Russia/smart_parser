﻿using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{
    public class Cell
    {
        //Gets the grid span of this cell (how many cells are merged).
        public virtual int GridSpan { get { return MergedColsCount;  } } 
        public virtual bool IsMerged { set; get; } = false;
        public virtual int FirstMergedRow { set; get; } = -1;
        public virtual int MergedRowsCount { set; get; } = -1;
        public virtual int MergedColsCount { set; get; } = 1;
        public virtual bool IsHeader { set; get; } = false;
        public virtual bool IsEmpty { set; get; } = true;
        public virtual string BackgroundColor { set; get; }
        public virtual string ForegroundColor { set; get; }

        public virtual string Text { set; get; } = "";

        public virtual string GetText(bool trim = true)
        {
            return Text;
        }

        public int Row { get; set; } = -1;
        public int Col { get; set; } = -1;

    };

    public class Row
    {
        public Row(IAdapter adapter, int row)
        {
            this.row = row;
            this.adapter = adapter;
            Cells = adapter.GetCells(row); 
        }

        public string GetContents(DeclarationField field)
        {
            var c = adapter.GetDeclarationField(row, field);
            if (c == null)
            {
                return "";
            }
            return c.GetText(true);
        }
        public ColumnOrdering ColumnOrdering
        {
            get
            {
                return adapter.ColumnOrdering;
            }
        }

        public bool IsEmpty()
        {
            return Cells.All(cell => cell.Text.IsNullOrWhiteSpace());
        }

        public List<Cell> Cells { get; set; }
        IAdapter adapter;
        int row; 
    }

    public class Rows
    {
        private IAdapter adapter;

        // ctor etc.

        public Row this[int index]
        {
            get
            {
                return adapter.GetRow(index);
            }
        }

        public Rows(IAdapter adapter)
        {
            this.adapter = adapter;
        }
    }


    public abstract class IAdapter
    {
        //        Cell GetCell(string cellNum);
        abstract public Cell GetCell(int row, int column);
        public virtual List<Cell> GetCells(int row)
        {
            throw new NotImplementedException();
        }

        public Rows Rows
        {
            get
            {
                return new Rows(this);
            }
        }

        public Row GetRow(int row)
        {
            return new Row(this, row);
        }

        public bool HasDeclarationField(DeclarationField field)
        {
            return ColumnOrdering.ColumnOrder.ContainsKey(field);
        }

        public Cell GetDeclarationField(int row, DeclarationField field)
        {
            return GetCell(row, Field2Col(field));
        }

        public string GetContents(int row, DeclarationField field)
        {
            return GetDeclarationField(row, field).GetText(true);
        }


        abstract public int GetRowsCount();
        abstract public int GetColsCount();
        //abstract public int GetColsCount(int Row);


        protected int Field2Col(DeclarationField field)
        {
            int index = -1;
            if (!ColumnOrdering.ColumnOrder.TryGetValue(field, out index))
            {
                //return -1;
                throw new SystemException("Field " + field.ToString() + " not found");
            }
            return index;
        }
        public virtual int GetColsCount(int Row)
        {
            throw new NotImplementedException();
        }



        public ColumnOrdering ColumnOrdering { get; set; }
        public virtual string GetTitle()
        {
            throw new NotImplementedException();
        }

        public string DocumentFile { set; get; }

        public virtual int GetWorkSheetCount()
        {
            return 1;
        }

        public virtual void SetCurrentWorksheet(int sheetIndex)
        {
            throw new NotImplementedException();
        }

        public virtual string GetWorksheetName()
        {
            return null;
        }

        public virtual int GetWorksheetIndex()
        {
            throw new NotImplementedException();
        }

    }
}
