DROPBOX=C:/Users/sokirko/Dropbox/RawDeclarations/document_files
SMART_PARSER=../../src/bin/Release/smart_parser.exe
TMPFOLDER=documents
HEADER_RECALL=header_recall.py

#python $HEADER_RECALL --action copy_data --dropbox-folder $DROPBOX --output-folder $TMPFOLDER 
#python $HEADER_RECALL --action process --smart-parser $SMART_PARSER  --output-folder $TMPFOLDER
#python $HEADER_RECALL --action report  --output-folder $TMPFOLDER

#all actions
python $HEADER_RECALL  --action full --dropbox-folder $DROPBOX --output-folder $TMPFOLDER --smart-parser $SMART_PARSER


