set DROPBOX=D:\programming\work_current\smart_parser\sample
set SMART_PARSER=..\..\src\bin\Release\netcoreapp3.1\smart_parser.exe
set TMPFOLDER=documents
set CORPUS_PROCESS=corpus_process.py

#python $CORPUS_PROCESS --action copy_data --dropbox-folder $DROPBOX --output-folder $TMPFOLDER 
#python $CORPUS_PROCESS --action process --smart-parser $SMART_PARSER  --output-folder $TMPFOLDER
#python $CORPUS_PROCESS --action report  --output-folder $TMPFOLDER

#all actions
python %CORPUS_PROCESS%  --action full --dropbox-folder %DROPBOX% --output-folder %TMPFOLDER% --smart-parser %SMART_PARSER%
