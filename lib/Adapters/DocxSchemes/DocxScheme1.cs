using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using System.Linq;
using DocumentFormat.OpenXml.Spreadsheet;
using Parser.Lib;
using Smart.Parser.Adapters;
using TI.Declarator.ParserCommon;
using Cell = Smart.Parser.Adapters.Cell;
using Table = DocumentFormat.OpenXml.Wordprocessing.Table;

namespace Smart.Parser.Lib.Adapters.DocxSchemes
{
    class DocxScheme1 : IDocxScheme
    {
        public override string GetTitle()
        {
            var docPart = Document.MainDocumentPart;
            var paragraphs = docPart.Document.Descendants<Paragraph>().ToList();
            var titleIdx = paragraphs.FindIndex(x => x.InnerText.Contains("за отчетный период"));
            var titleList = paragraphs.Take(titleIdx + 1).ToList();
            titleList.ForEach(x => Title = Title + x.InnerText + " ");
            return Title;
        }

        public override string GetPersonName()
        {
            var words = Regex.Split(Title, @"[\,\s\n]+").ToList();
            var idx = words.FindIndex(TextHelpers.CanBePatronymic);
            if (idx < 2)
                throw new SmartParserException("No person name found in DocxScheme1");

            // в родительном падеже, к сожалению
            return String.Join(" ", words.Skip(idx - 2).Take(3));
        }

        public override bool CanProcess(WordprocessingDocument document)
        {
            var docPart = document.MainDocumentPart;
            var tables = docPart.Document.Descendants<Table>().ToList();
            if (tables.Count != 5)
                return false;

            var paragraphs = docPart.Document.Descendants<Paragraph>().ToList();
            var titles = paragraphs.FindAll(x => x.InnerText.ToLower().Contains("раздел"));

            if (titles.Count != 3)
                return false;

            if (!titles[0].InnerText.Contains("Сведения о доходах"))
                return false;
            if (!titles[1].InnerText.Contains("Сведения об имуществе"))
                return false;
            if (!titles[2].InnerText.Contains("Сведения об источниках"))
                return false;

            var firstTableTitlesOk = tables.Any(
                x => x.Descendants<TableRow>().Any(
                    y => y.InnerText.OnlyRussianLowercase().Contains("ппвиддоходавеличинадоходаруб")));

            return firstTableTitlesOk;
        }

        public override void ProcessMainPerson(string name, OnePersonAdapter adapter)
        {
            var tables = Document.MainDocumentPart.Document.Descendants<Table>().ToList().Take(5).ToList();
            var line = new List<string>
            {
                name,
                tables[0].Descendants<TableRow>().ToList()[1].Descendants<TableCell>().ToList()[2].InnerText,
            };
            line.AddRange(Enumerable.Repeat<string>("", 8));
            adapter.AddRow(line);

            var realestateData = ExtractCellsFromTable(
                adapter, tables[2], 
                1, 3, 
                new List<string> {"нет", "видимущества"});
            realestateData.ForEach(x => adapter.AddRow(new List<string>
                {
                    "", "", x[0], x[1], x[2], "", "", "", "", ""
                })
            );
            
            var stateEstate = ExtractCellsFromTable(
                adapter, tables[4], 
                1, 3, 
                new List<string> {"нет", "видимущества"});
            stateEstate.ForEach(x => adapter.AddRow(new List<string> 
            {
                "", "", "", "", "", x[0], x[2], x[1], "", ""
            }));
            
            var vehicleData = ExtractCellsFromTable(
                adapter, tables[3], 
                1, 1, 
                new List<string> {"нет", "видимаркатранспортногосредства"});
            vehicleData.ForEach(x => adapter.AddRow(Enumerable.Repeat(" ", 8).Append(x[0]).Append(x[1]).ToList()));
        }

        private static List<List<string>> ExtractCellsFromTable(OnePersonAdapter adapter, Table table,
            int columnStart, int columnEnd, List<string> skipList)
        {
            var result = new List<List<string>>();
            var lastType = "";
            foreach (var row in table.Descendants<TableRow>().ToList())
            {
                var cells = row.Descendants<TableCell>().ToList();
                if (cells.Count == 1)
                {
                    lastType = cells[0].InnerText;
                    continue;
                }
                if (skipList.Any(x => x == cells[1].InnerText.OnlyRussianLowercase()))
                    continue;
                if (cells[columnStart].InnerText.OnlyRussianLowercase() == string.Empty)
                    continue;
                var line = new List<string>();
                for (int i=columnStart; i<=columnEnd; i++) {
                    line.Add(cells[i].InnerText);
                    line.Add(lastType);
                }
                result.Add(line);
            }

            return result;
        }
    }
}