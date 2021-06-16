DROPBOX=C:/tmp/examples.header_recall/sample
SMART_PARSER=C:/tmp/smart_parser/smart_parser/src/bin/Release/netcoreapp3.1/smart_parser.exe
TMPFOLDER=documents
CORPUS_PROCESS=C:/tmp/smart_parser/smart_parser/tools/CorpusProcess/corpus_process.py
cp c:/tmp/aspose_lic/lic.bin .
if [ ! -f "lic.bin" ]; then
    echo "lic.bin does not exist"
fi

python $CORPUS_PROCESS --action copy_data --dropbox-folder $DROPBOX --output-folder $TMPFOLDER 
python $CORPUS_PROCESS --action process --smart-parser $SMART_PARSER  --process-count 5 --output-folder $TMPFOLDER
python $CORPUS_PROCESS --action report  --output-folder $TMPFOLDER

#all actions
#python $CORPUS_PROCESS  --action full --dropbox-folder $DROPBOX --output-folder $TMPFOLDER --smart-parser $SMART_PARSER


