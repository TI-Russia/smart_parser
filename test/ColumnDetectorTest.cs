using StringHelpers;
using SmartParser.Lib;

using System;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.IO;


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

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 12);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.NameOrRelativeType].BeginColumn == 0);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Occupation].BeginColumn == 1);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateType].BeginColumn == 2);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateOwnershipType].BeginColumn == 3);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateSquare].BeginColumn == 4);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateCountry].BeginColumn == 5);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyType].BeginColumn == 6);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertySquare].BeginColumn == 7);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyCountry].BeginColumn == 8);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Vehicle].BeginColumn == 9);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome].BeginColumn == 10);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DataSources].BeginColumn == 11);
        }

        [TestMethod]
        public void EmptyRealStateTypeColumnDetectorTest1()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "rabotniki_podved_organizacii_2013.xlsx");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);
            ColumnByDataPredictor.InitializeIfNotAlready();
            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Number].BeginColumn == 0);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.NameOrRelativeType].BeginColumn == 1);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Occupation].BeginColumn == 2);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateType].BeginColumn == 3);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateOwnershipType].BeginColumn == 4);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateSquare].BeginColumn == 5);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateCountry].BeginColumn == 6);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyType].BeginColumn == 7);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertySquare].BeginColumn == 8);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyCountry].BeginColumn == 9);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Vehicle].BeginColumn == 10);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome].BeginColumn == 11);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DataSources].BeginColumn == 12);
        }

 
        [TestMethod]
        public void ColumnDetectorTest1TIAdapter()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "fsin_2016_extract.xlsx");
            
            //IAdapter adapter = NpoiExcelAdapter.CreateAdapter(xlsxFile);
            // aspose do not want to read column widthes from this file, use aspose
            // fix it in the future (is it a bug in Npoi library?).  

            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 12);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.NameOrRelativeType].BeginColumn == 0);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Occupation].BeginColumn == 1);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateType].BeginColumn == 2);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateOwnershipType].BeginColumn == 3);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateSquare].BeginColumn == 4);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.OwnedRealEstateCountry].BeginColumn == 5);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyType].BeginColumn == 6);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertySquare].BeginColumn == 7);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.StatePropertyCountry].BeginColumn == 8);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.Vehicle].BeginColumn == 9);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome].BeginColumn == 10);
            Assert.IsTrue(ordering.ColumnOrder[DeclarationField.DataSources].BeginColumn == 11);
        }

        [TestMethod]
        public void RealEstateColumnDetector()
        {
            string docxFile = Path.Combine(TestUtil.GetTestDataPath(), "glav_44_2010.doc");
            IAdapter adapter = OpenXmlWordAdapter.CreateAdapter(docxFile, -1);

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 9);
        }

        [TestMethod]
        public void FixVehicleColumns()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "17497.xls");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile, -1);
            ColumnByDataPredictor.InitializeIfNotAlready();

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(15, ordering.ColumnOrder.Count);
            Assert.IsTrue(ordering.ContainsField(DeclarationField.VehicleType));
            Assert.IsTrue(ordering.ContainsField(DeclarationField.VehicleModel));
            Assert.IsFalse(ordering.ContainsField(DeclarationField.Vehicle));
        }


        [TestMethod]
        public void RedundantColumnDetector()
        {
            string docxFile = Path.Combine(TestUtil.GetTestDataPath(), "18664.docx");
            IAdapter adapter = OpenXmlWordAdapter.CreateAdapter(docxFile, -1);

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 13);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.AcquiredProperty].BeginColumn, 11);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.MoneySources].BeginColumn, 12);
        }

        [TestMethod]
        public void TwoRowHeaderEmptyTopCellTest()
        {
            string docxFile = Path.Combine(TestUtil.GetTestDataPath(), "57715.doc");
            IAdapter adapter = OpenXmlWordAdapter.CreateAdapter(docxFile, -1);

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 13);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.Vehicle].BeginColumn, 10);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome].BeginColumn, 11);
        }

        [TestMethod]
        public void SpendingsWrongColumnTest()
        {
            string docxFile = Path.Combine(TestUtil.GetTestDataPath(), "82442.doc");
            IAdapter adapter = OpenXmlWordAdapter.CreateAdapter(docxFile, -1);

            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.DeclaredYearlyIncome].BeginColumn, 1);
        }

        

        [TestMethod]
        public void TwoRowHeaderEmptyTopCellTest2()
        {
            string xlsxFile = Path.Combine(TestUtil.GetTestDataPath(), "customs-tworow-header.xls");
            IAdapter adapter = AsposeExcelAdapter.CreateAdapter(xlsxFile);

            ColumnByDataPredictor.InitializeIfNotAlready();
            TableHeader ordering = TableHeaderRecognizer.ExamineTableBeginning(adapter);
            Assert.AreEqual(ordering.ColumnOrder.Count, 14);
            Assert.AreEqual(ordering.ColumnOrder[DeclarationField.Occupation].BeginColumn, 2);
        }

    }
}
