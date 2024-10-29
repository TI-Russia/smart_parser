using Azure;
using Azure.AI.FormRecognizer.DocumentAnalysis;

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

using SmartParser.Lib;

using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Lib.Adapters.Azure
{
    public class AzureTableToParserMapper
    {
        public int StartRowIndex { get; set; } = 0;
        public DocumentTable Table { get; set; }
        public TableHeader TableHeader { get; set; }
        public IDictionary<int, Cell[]> Cells { get; set; } = new Dictionary<int, Cell[]>();
        public bool IsNormalized { get; set; }
    }
    public class AzureTableCell : Cell
    {
        public AzureTableCell(int globalRowIndex, int row, int col) : this(globalRowIndex, string.Empty, row, col, 1, 1)
        {
        }
        public AzureTableCell(int globalRowIndex, DocumentTableCell cell) : this(globalRowIndex, cell.Content, cell.RowIndex, cell.ColumnIndex, cell.RowSpan, cell.ColumnSpan)
        {
        }

        public AzureTableCell(int globalRowIndex, string text, int row, int col, int mergerow, int mergecol)
        {
            Row = globalRowIndex + row;
            Col = col;
            Text = text;
            MergedRowsCount = 1;
            MergedColsCount = 1;
            IsEmpty = string.IsNullOrWhiteSpace(text);
        }

    }


    public class AzureFormRecognizer : IAdapter
    {
        bool isDebug = true;
        ICollection<AzureTableToParserMapper> DataTables;
        DocumentAnalysisClient client;
        string inputFile;
        AnalyzeResult doc;

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
            var azureSell = DataTables.SelectMany(x => x.Cells).FirstOrDefault(x => x.Key == row).Value.FirstOrDefault(x => x.Col == column);
            return azureSell;
        }

        public override int GetColsCount()
        {
            var cols = DataTables.OrderByDescending(x => x.TableHeader?.ColumnOrder?.Count).FirstOrDefault().TableHeader?.ColumnOrder?.Count;
            if (!cols.HasValue)
            {
                cols = DataTables.Max(x => x.Table.ColumnCount);
            }
            return cols ?? 0;
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
            var data = new List<string>();
            var title = "";
            int? year = 0;
            var ministry = "";
            var titlefound = false;
            foreach (var paragr in doc.Paragraphs)
            {
                var text = paragr.Content.ToLower();
                bool has_title_words = Array.Exists(TableHeaderRecognizer.TitleStopWords, text.Contains);
                if (!titlefound)
                {
                    if (!has_title_words || (text.StartsWith("за") && text.EndsWith("год")))
                    {
                        titlefound = true;
                        continue;
                    }
                }

                if (TableHeaderRecognizer.GetValuesFromTitle(paragr.Content, ref title, ref year, ref ministry))
                {
                    data.Add(paragr.Content);
                }
            }
            return string.Join(" ", data);
        }



        public override int GetTablesCount()
        {
            return doc?.Tables?.Count ?? 0;
        }

        public async Task RecognizeForm()
        {
            try
            {
                Logger.Info("Uploading file to Azure Form Recognizer : " + inputFile);
                DataTables = new List<AzureTableToParserMapper>();
                byte[] fileBytes = File.ReadAllBytes(inputFile);
                using var stream = new MemoryStream(fileBytes);
                var operation = await client.AnalyzeDocumentAsync(WaitUntil.Completed, "prebuilt-document", stream);
                doc = operation.Value;
                Logger.Info($"Azure Form Recognizer: {doc.Tables.Count} tables found");

                var rowIndex = 0;
                foreach (var table in doc.Tables)
                {
                    //skip suspicious tables
                    if (table.Cells.Where(x => x.ColumnSpan == 1).Max(x => x.ColumnIndex) < 3)
                    {
                        continue;
                    }

                    var parsedTable = new AzureTableToParserMapper { StartRowIndex = rowIndex, Table = table };

                    for (int row = 0; row < table.RowCount; row++)
                    {
                        var cells = table.Cells.Where(c => c.RowIndex == row).ToList();
                        parsedTable.Cells.Add(rowIndex, cells.Select(x => new AzureTableCell(parsedTable.StartRowIndex, x)).ToArray());
                        rowIndex++;
                    }
                    DataTables.Add(parsedTable);

                    var header = table.Cells.Where(c => c.Kind == DocumentTableCellKind.ColumnHeader).ToList();
                    parsedTable.TableHeader = MapToHeaderColumns(parsedTable, header);
                }

                foreach (var table in DataTables)
                {

                    ValidateCommonHeaders(table);
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
        void ValidateCommonHeaders(AzureTableToParserMapper mappedTable)
        {
            DataTables.Add(mappedTable);

            // find the largest table
            var largestTable = DataTables.OrderByDescending(x => x.TableHeader.ColumnOrder.Count).FirstOrDefault();

            var largestTableColumns = largestTable.TableHeader.ColumnOrder.Keys.ToList();
            foreach (var table in DataTables.Where(x => x != largestTable))
            {
                table.Cells = new Dictionary<int, Cell[]>();
                var currentTableColumnIndices = new Dictionary<DeclarationField, int>();
                int colIndex = 0;
                foreach (var columnName in table.TableHeader.ColumnOrder.Keys)
                {
                    currentTableColumnIndices[columnName] = colIndex;
                    colIndex++;
                }

                // Process each row in the table
                int rowIndex = table.StartRowIndex;
                table.Cells = new Dictionary<int, Cell[]>();
                for (int i = 0; i < table.Table.RowCount; i++)
                {
                    var cells = table.Table.Cells.Where(c => c.RowIndex == i).ToArray();

                    var newRowCells = new AzureTableCell[largestTableColumns.Count];

                    for (int j = 0; j < largestTableColumns.Count; j++)
                    {
                        var columnName = largestTableColumns[j];

                        if (currentTableColumnIndices.TryGetValue(columnName, out int colIndexInCurrentTable))
                        {
                            // Column exists in current table, get the cell
                            newRowCells[j] = new AzureTableCell(table.StartRowIndex, cells[colIndexInCurrentTable]);
                        }
                        else
                        {
                            // Column is missing in current table, insert an empty cell
                            newRowCells[j] = new AzureTableCell(table.StartRowIndex, rowIndex, j);
                        }
                    }

                    table.Cells[rowIndex] = newRowCells;
                    rowIndex++;

                }
            }
            mappedTable.IsNormalized = true;
        }

        TableHeader MapToHeaderColumns(AzureTableToParserMapper parsedTable, ICollection<DocumentTableCell> header)
        {
            var headerCells = header.Select(c => new AzureTableCell(parsedTable.StartRowIndex, c)).Cast<Cell>().ToList();
            var tableHeader = new TableHeader();
            TableHeaderRecognizer.MapColumnTitlesToInnerConstants(this, headerCells, tableHeader);
            return tableHeader;
        }
        protected override List<Cell> GetCells(int row, int maxColEnd)
        {

            var cells = DataTables.SelectMany(x => x.Cells)?.FirstOrDefault(x => x.Key == row).Value?.ToList();
            return cells ?? new List<Cell>();
        }


        public bool Validate()
        {
            return !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AZURE_FR_ENDPOINT")) &&
                !string.IsNullOrEmpty(Environment.GetEnvironmentVariable("AZURE_FR_APIKEY"));
        }
    }
}