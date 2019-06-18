using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using Smart.Parser.Adapters;

namespace test
{
    [TestClass]
    public class NpoiExcelAdapterBasic
    {
        private IAdapter GetAdapter()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "Test.xlsx");
            return  NpoiExcelAdapter.CreateAdapter(xlsxFile);
        }
        /// <summary>
        /// Read the contents of single non-merged cell
        /// </summary>
        [TestMethod]
        public void GetNonMergedCell()
        {
            var adapter = GetAdapter();
            Cell cell = adapter.GetCell(0, 13);

            Assert.IsNotNull(cell);

            Assert.IsFalse(cell.IsMerged);
            Assert.AreEqual(0, cell.FirstMergedRow);
            Assert.AreEqual(1, cell.MergedRowsCount);
            Assert.AreEqual(false, cell.IsEmpty);
            Assert.AreEqual("TestCell", cell.Text);
        }

        /// <summary>
        /// Get cell by its row and column numbers
        /// </summary>
        [TestMethod]
        public void GetCellByIndex()
        {
            var adapter = GetAdapter();
            Cell cell1 = adapter.GetCell(0, 13);

            // Check that it is indeed the same cell
            Assert.IsNotNull(cell1);

            Assert.AreEqual(false, cell1.IsMerged);
            Assert.AreEqual(1, cell1.MergedRowsCount);
            Assert.AreEqual(false, cell1.IsEmpty);
            Assert.AreEqual("TestCell", cell1.Text);
        }


        /// <summary>
        /// Empty cells are the cells that contain nothing (except whitespace)
        /// </summary>
        [TestMethod]
        public void GetEmptyCell()
        {
            /// A merged empty cell that contains nothing
            var adapter = GetAdapter(); 
            Cell cell1 = adapter.GetCell(75, 2);
            Assert.IsNotNull(cell1);
            Assert.AreEqual(true, cell1.IsEmpty);
            Assert.AreEqual("", cell1.Text);

            // A single empty cell that contains only (4) whitespace characters
            Cell cell2 = adapter.GetCell(0, 14);
            Assert.IsNotNull(cell2);
            Assert.AreEqual(true, cell2.IsEmpty);
            Assert.AreEqual("    ", cell2.Text);
        }

        /// <summary>
        /// Read the contents of a merged cell spanning several rows
        /// </summary>
        [TestMethod]
        public void GetMergedCell()
        {
            var adapter = GetAdapter();
            Cell cell = adapter.GetCell(4, 1);
            Assert.IsNotNull(cell);

            Assert.AreEqual(true, cell.IsMerged);
            Assert.AreEqual(8, cell.MergedRowsCount);
            Assert.AreEqual(false, cell.IsEmpty);
            Assert.AreEqual("Осипов А. М.", cell.Text);
        }

        [TestMethod]
        public void GetRowsCount()
        {
            var adapter = GetAdapter();
            Assert.AreEqual(79, adapter.GetRowsCount());
        }
    }
}
