﻿using Smart.Parser.Adapters;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TI.Declarator.ParserCommon;

namespace Smart.Parser.Adapters
{

    class AsposeDocCell : Cell
    {
        public AsposeDocCell(Aspose.Words.Tables.Cell cell)
        {
            if (cell == null)
                return;

            String cellText = cell.ToString(Aspose.Words.SaveFormat.Text).Trim();

            Text = cellText;

            IsEmpty = String.IsNullOrEmpty(Text);


        }
    }

    public class AsposeDocAdapter : IAdapter
    {
        public static IAdapter CreateAdapter(string fileName)
        {
            return new AsposeDocAdapter(fileName);
        }

        public override Cell GetCell(int row, int column)
        {
            Aspose.Words.Tables.Cell cell = table.Rows[row].Cells[column];
            return new AsposeDocCell(cell);
        }

        public override List<Cell> GetCells(int row, int maxColEnd = -1)
        {
            int index = 0;
            List<Cell> result = new List<Cell>();
            IEnumerator enumerator = table.Rows[row].GetEnumerator();
            int range_end = -1;
            while (enumerator.MoveNext())
            {
                Aspose.Words.Tables.Cell cell = (Aspose.Words.Tables.Cell)enumerator.Current;
                if (index < range_end)
                {
                    index++;
                    continue;
                }

                result.Add(new AsposeDocCell(cell));

                index++;
            }
            return result;
        }



        public override int GetRowsCount()
        {
            return table.Rows.Count;
        }

        public override int GetColsCount()
        {
            return table.Rows[0].Count;
        }

        public override string GetTitleOutsideTheTable()
        {
            return title;
        }


        private AsposeDocAdapter(string fileName)
        {
            DocumentFile = fileName;
            Aspose.Words.Document doc = new Aspose.Words.Document(fileName);
            Aspose.Words.NodeCollection tables = doc.GetChildNodes(Aspose.Words.NodeType.Table, true);

            int count = tables.Count;
            if (count == 0)
            {
                throw new SystemException("No table found in document " + fileName);
            }


            table = (Aspose.Words.Tables.Table)tables[0];

            Aspose.Words.Node node = table;
            while (node.PreviousSibling != null)
            { 
                node = node.PreviousSibling;
            }
            var text = new StringBuilder();
            while (node.NextSibling != table)
            {
                text.Append(node.ToString());
                node = node.NextSibling;
            }

            title = text.ToString();
        }

        private Aspose.Words.Tables.Table table;
        private string title;
    }
}
