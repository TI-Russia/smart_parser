using Azure;
using Azure.AI.FormRecognizer.DocumentAnalysis;
using SmartParser.Lib;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Lib.Adapters.Azure
{
    public class AzureTableCell : Cell
    {
        public AzureTableCell(string text, int row, int col)
        {
            Text = text;
            Row = row;
            Col = col;
            IsEmpty = string.IsNullOrWhiteSpace(Text);
        }
        public AzureTableCell(IAdapter.TJsonCell cell)
        {
            Text = cell.t;
            MergedColsCount = cell.mc;
            MergedRowsCount = cell.mr;
            IsEmpty = string.IsNullOrWhiteSpace(Text);
            Row = cell.r;
            Col = cell.c;
        }
    }


    public class AzureFormRecognizer : IAdapter
    {
        bool isDebug = true;
        private List<OpenXmlTableRow> TableRows;
        DocumentAnalysisClient client;
        string inputFile;
        AnalyzeResult doc;
        DocumentTable MainTable => doc?.Tables.Where(t => t.ColumnCount >= 4).FirstOrDefault();

        public AzureFormRecognizer(string inputFile)
        {
            this.inputFile = inputFile;
            DocumentFile = inputFile;
            var endpoint = Environment.GetEnvironmentVariable("AZURE_FR_ENDPOINT");
            var apiKey = Environment.GetEnvironmentVariable("AZURE_FR_APIKEY");
            client = new DocumentAnalysisClient(new Uri(endpoint), new AzureKeyCredential(apiKey));

        }

        public override Cell GetCell(int row, int column)
        {
            var azureSell =MainTable.Cells.FirstOrDefault(c => c.RowIndex == row && c.ColumnIndex == column);
            if (azureSell != null)
            {
                return new AzureTableCell(azureSell.Content, azureSell.RowIndex, azureSell.ColumnIndex);

            }
            return null;
        }

        public override int GetColsCount()
        {
            return MainTable?.ColumnCount ?? 0;
        }

        public override int GetRowsCount()
        {
            return MainTable?.RowCount ?? 0;
        }

        public override List<Cell> GetUnmergedRow(int row)
        {
            throw new NotImplementedException();
        }
        public override string GetTitleOutsideTheTable()
        {
            return doc?.Paragraphs.FirstOrDefault()?.Content;
        }
        public override int GetTablesCount()
        {
            return doc?.Tables.Count ?? 0;
        }

        public async Task RecognizeForm()
        {
            try
            {
                byte[] fileBytes = File.ReadAllBytes(inputFile);
                using var stream = new MemoryStream(fileBytes);

                var operation = await client.AnalyzeDocumentAsync(WaitUntil.Completed, "prebuilt-document", stream);
                doc = operation.Value;
                Logger.Info($"Azure Form Recognizer: {doc.Tables.Count} tables found");
            }
            catch (RequestFailedException e)
            {
                Logger.Error($"Azure Form Recognizer Error: {e.Message}");
                Logger.Error($"Error Code: {e.ErrorCode}");
                Logger.Error($"Status: {e.Status}");
            }
            catch (Exception e)
            {
                Logger.Error($"Exception: {e.Message}");
            }
        }

        protected override List<Cell> GetCells(int row, int maxColEnd)
        {
            var table = MainTable;
            if (table == null)
            {
                return new List<Cell>();
            }
            var cells = new List<Cell>();
            for (int col = 0; col < table.ColumnCount; col++)
            {
                var azureCell = table.Cells.FirstOrDefault(c => c.RowIndex == row && c.ColumnIndex == col);
                if (azureCell != null)
                {
                    cells.Add(new AzureTableCell(azureCell.Content, azureCell.RowIndex, azureCell.ColumnIndex));

                }
            }
            return cells;
        }


        public bool Validate()
        {
            return !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AZURE_FR_ENDPOINT")) &&
                !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AZURE_FR_APIKEY"));
        }
    }
}