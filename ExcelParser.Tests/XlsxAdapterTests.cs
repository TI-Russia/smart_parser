using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using Smart.Parser.Adapters;

namespace ExcelParser.Tests
{
    [TestClass]
    public class XlsxAdapterTests
    {
        /// <summary>
        /// Read the contents of single non-merged cell
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetNonMergedCell()
        {
            var adapter = NpoiExcelAdapter.CreateAdapter("Test.xlsx");
            Cell cell = adapter.GetCell(0, 13);

            Assert.IsNotNull(cell);

            Assert.IsFalse(cell.IsMerged);
            Assert.AreEqual(0, cell.FirstMergedRow);
            Assert.AreEqual(1, cell.MergedRowsCount);
            Assert.AreEqual(false, cell.IsEmpty);
            Assert.AreEqual(null, cell.BackgroundColor);
            Assert.AreEqual("5B9BD5", cell.ForegroundColor);
            Assert.AreEqual("TestCell", cell.Text);
        }

        /// <summary>
        /// Get cell by its row and column numbers
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetCellByIndex()
        {
            var adapter = NpoiExcelAdapter.CreateAdapter("Test.xlsx");
            Cell cell1 = adapter.GetCell(0, 13);

            // Check that it is indeed the same cell
            Assert.IsNotNull(cell1);

            Assert.AreEqual(false, cell1.IsMerged);
            Assert.AreEqual(1, cell1.MergedRowsCount);
            Assert.AreEqual(false, cell1.IsEmpty);
            Assert.AreEqual(null, cell1.BackgroundColor);
            Assert.AreEqual("5B9BD5", cell1.ForegroundColor);
            Assert.AreEqual("TestCell", cell1.Text);
        }


        /// <summary>
        /// Empty cells are the cells that contain nothing (except whitespace)
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetEmptyCell()
        {
            /// A merged empty cell that contains nothing
            var adapter = NpoiExcelAdapter.CreateAdapter("Test.xlsx");
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
        [DeploymentItem("Test.xlsx")]
        public void GetMergedCell()
        {
            var adapter = NpoiExcelAdapter.CreateAdapter("Test.xlsx");
            Cell cell = adapter.GetCell(7, 1);
            Assert.IsNotNull(cell);

            Assert.AreEqual(true, cell.IsMerged);
            Assert.AreEqual(8, cell.MergedRowsCount);
            Assert.AreEqual(false, cell.IsEmpty);
            Assert.AreEqual(null, cell.BackgroundColor);
            Assert.AreEqual(null, cell.ForegroundColor);
            Assert.AreEqual("Осипов А. М.", cell.Text);
        }

        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetRowsCount()
        {
            var adapter = NpoiExcelAdapter.CreateAdapter("Test.xlsx");
            Assert.AreEqual(80, adapter.GetRowsCount());
        }
    }
}
