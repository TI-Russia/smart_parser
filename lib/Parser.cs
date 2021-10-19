using StringHelpers;
using SmartParser.Lib;

using System;
using System.Threading;
using System.Collections.Generic;
using System.Linq;


namespace SmartParser.Lib
{
    
    public class Parser : ParserBase
    { 
        bool FailOnRelativeOrphan;
        public int NameOrRelativeTypeColumn { set; get; } = 1;

        public Parser(IAdapter adapter, bool failOnRelativeOrphan = true)
        {
            Adapter = adapter;
            FailOnRelativeOrphan = failOnRelativeOrphan;
            ParserNumberFormatInfo.NumberDecimalSeparator = ",";
            
        }
        public static void InitializeSmartParser()
        {
            SmartParser.Lib.AsposeLicense.SetAsposeLicenseFromEnvironment();

            var culture = new System.Globalization.CultureInfo("ru-RU");
            Thread.CurrentThread.CurrentCulture = culture;
            var envVars = Environment.GetEnvironmentVariables();
            if (envVars.Contains("DECLARATOR_CONV_URL"))
            {
                IAdapter.ConvertedFileStorageUrl = envVars["DECLARATOR_CONV_URL"].ToString();
            }
        }

        static public Declaration InitializeDeclaration(IAdapter adapter,  ColumnOrdering columnOrdering, int? user_documentfile_id)
        {
            // parse filename
            int? documentfile_id;
            string archive;
            bool result = DataHelper.ParseDocumentFileName(adapter.DocumentFile, out documentfile_id, out archive);
            if (user_documentfile_id.HasValue)
                documentfile_id = user_documentfile_id;

            DeclarationProperties properties = new DeclarationProperties()
            {
                SheetTitle = columnOrdering.Title,
                Year = columnOrdering.Year,
                DocumentFileId = documentfile_id,
                ArchiveFileName = archive,
                SheetNumber = adapter.GetWorksheetIndex(),
                DocumentUrl = adapter.GetDocumentUrlFromMetaTag()
            };
            if (columnOrdering.YearFromIncome != null)
            {
                if (properties.Year != null)
                {
                    properties.Year = Math.Max(columnOrdering.YearFromIncome.Value, properties.Year.Value);
                }
                else
                {
                    properties.Year = columnOrdering.YearFromIncome;
                }
            }
            Declaration declaration = new Declaration()
            {
                Properties = properties
            };
            return declaration;
        }

        public Declaration Parse(ColumnOrdering columnOrdering, bool updateTrigrams, int? documentfile_id)
        {
            var firstPassStartTime = DateTime.Now;
            Declaration declaration = InitializeDeclaration(Adapter, columnOrdering, documentfile_id);
            TBorderFinder borderFinder = new TBorderFinder(Adapter, declaration, FailOnRelativeOrphan);
            borderFinder.FindBordersAndPersonNames(columnOrdering, updateTrigrams);
            if (ColumnOrdering.SearchForFioColumnOnly)
                return declaration;
            TSecondPassParser secondPassParser = new TSecondPassParser(Adapter);
            int declarantCount = secondPassParser.ParseDeclarants(declaration);
            double seconds = DateTime.Now.Subtract(firstPassStartTime).TotalSeconds;
            Logger.Info("Final Rate: {0:0.00} declarant in second", declarantCount / seconds);
            double total_seconds = DateTime.Now.Subtract(firstPassStartTime).TotalSeconds;
            Logger.Info("Total time: {0:0.00} seconds", total_seconds);
            return declaration;
        }



        public IAdapter Adapter { get; set; }
    }
}
