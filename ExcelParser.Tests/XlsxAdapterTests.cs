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
        /// Read the contests of single non-merged cell
        /// </summary>
        [TestMethod]
        [DeploymentItem("Test.xlsx")]
        public void GetNonMergedCell()
        {
            string testFilePath = Path.GetFullPath("Test.xlsx");
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
    }
}
