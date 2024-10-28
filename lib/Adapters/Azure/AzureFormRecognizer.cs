using Azure;
using Azure.AI.FormRecognizer.DocumentAnalysis;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

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
        public AzureTableCell(DocumentTableCell cell)
        {
            Text = cell.Content;
            Row = cell.RowIndex;
            Col = cell.ColumnIndex;
            MergedColsCount = cell.ColumnSpan;
            MergedRowsCount = cell.RowSpan;
            IsEmpty = string.IsNullOrWhiteSpace(Text);
        }

    }


    public class AzureFormRecognizer : IAdapter
    {
        bool isDebug = true;
        IDictionary<int, List<DocumentTableCell>> AllTableRows;
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
            var azureSell = MainTable.Cells.FirstOrDefault(c => c.RowIndex == row && c.ColumnIndex == column);
            if (azureSell != null)
            {
                return new AzureTableCell(azureSell);

            }
            return null;
        }

        public override int GetColsCount()
        {
            return MainTable?.ColumnCount ?? 0;
        }

        public override int GetRowsCount()
        {
            return doc?.Tables.Sum(t => t.RowCount) ?? 0;
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
            return doc?.Tables?.Count ?? 0;
        }

        public async Task RecognizeForm()
        {
            try
            {
                AllTableRows = new Dictionary<int, List<DocumentTableCell>>();
                byte[] fileBytes = File.ReadAllBytes(inputFile);
                using var stream = new MemoryStream(fileBytes);

                var operation = await client.AnalyzeDocumentAsync(WaitUntil.Completed, "prebuilt-document", stream);
                doc = operation.Value;
                Logger.Info($"Azure Form Recognizer: {doc.Tables.Count} tables found");

                var rowIndex = 0;
                foreach (var table in doc.Tables)
                {
                    for (int row = 0; row < table.RowCount; row++)
                    {
                        var cells = table.Cells.Where(c => c.RowIndex == row).ToList();
                        AllTableRows.Add(rowIndex, cells);
                        rowIndex++;
                    }
                }
            }
            catch (RequestFailedException e)
            {
                var resp = e.GetRawResponse();
                var error = JsonConvert.DeserializeObject<JObject>(resp.Content.ToString());
                Logger.Error($"Azure Form Recognizer Error: {error["error"]["innererror"]["message"]}");
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

            var cells = new List<Cell>();
            var tableCells = AllTableRows[row];
            foreach (var azureCell in tableCells)
            {
                cells.Add(new AzureTableCell(azureCell));

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