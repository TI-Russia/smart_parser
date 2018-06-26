using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using Smart.Parser.Adapters;
using TI.Declarator.ExcelParser;

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
            var adapter = XlsxParser.GetAdapter("Test.xlsx");
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
        /// Get cell by its alphanumeric index (e.g. G18)
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetCellByIndex()
        {
            var adapter = XlsxParser.GetAdapter("Test.xlsx");
            // We try to get the same cell using 2 different approaches:
            // by row/column indexes and through cell reference
            // note that in the first case the indexes are zero-based
            Cell cell1 = adapter.GetCell(0, 13);
            Cell cell2 = adapter.GetCell("N1");

            // Check that it is indeed the same cell
            Assert.IsNotNull(cell1);
            Assert.IsNotNull(cell2);

            Assert.AreEqual(cell1.IsMerged, cell2.IsMerged);
            Assert.AreEqual(cell1.MergedRowsCount, cell2.MergedRowsCount);
            Assert.AreEqual(cell1.IsEmpty, cell2.IsEmpty);
            Assert.AreEqual(cell1.BackgroundColor, cell2.BackgroundColor);
            Assert.AreEqual(cell1.ForegroundColor, cell2.ForegroundColor);
            Assert.AreEqual(cell1.Text, cell2.Text);
        }


        /// <summary>
        /// Empty cells are the cells that contain nothing (except whitespace)
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetEmptyCell()
        {
            /// A merged empty cell that contains nothing
            var adapter = XlsxParser.GetAdapter("Test.xlsx");
            Cell cell1 = adapter.GetCell("C76");
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
            var adapter = XlsxParser.GetAdapter("Test.xlsx");
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
            var adapter = XlsxParser.GetAdapter("Test.xlsx");
            Assert.AreEqual(80, adapter.GetRowsCount());
        }
    }
}
