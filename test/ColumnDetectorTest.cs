using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using TI.Declarator.ExcelParser;
using System.IO;
using Smart.Parser.Lib;

namespace test
{
    [TestClass]
    public class ColumnDetectorTest
    {
        [TestMethod]
        public void ColumnDetectorTest1()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);

            ColumnOrdering ordering = ColumnDetector.ExamineHeader(adapter);
            Assert.IsTrue(ordering.ColumnOrder.Count == 12);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.NameOrRelativeType] == 0);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Occupation] == 1);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateType] == 2);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateOwnershipType] == 3);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateArea] == 4);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateCountry] == 5);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyType] == 6);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyArea] == 7);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyCountry] == 8);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Vehicle] == 9);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome] == 10);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DataSources] == 11);
        }

        [TestMethod]
        public void ColumnDetectorTest1TIAdapter()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");
            IAdapter adapter = XlsxParser.GetAdapter(xlsxFile);

            ColumnOrdering ordering = ColumnDetector.ExamineHeader(adapter);
            Assert.IsTrue(ordering.ColumnOrder.Count == 12);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.NameOrRelativeType] == 0);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Occupation] == 1);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateType] == 2);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateOwnershipType] == 3);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateArea] == 4);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateCountry] == 5);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyType] == 6);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyArea] == 7);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyCountry] == 8);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Vehicle] == 9);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome] == 10);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DataSources] == 11);
        }
    }
}
