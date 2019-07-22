DROPBOX=C:/Users/sokirko/Dropbox/RawDeclarations/document_files
SMART_PARSER=C:/tmp/smart_parser/smart_parser/src/bin/Release/smart_parser.exe
CORPUS_PROCESS=C:/tmp/smart_parser/smart_parser/tools/CorpusProcess/corpus_process.py
TMPFOLDER=documents

python $CORPUS_PROCESS --action copy_data --dropbox-folder $DROPBOX --output-folder $TMPFOLDER 
mv _files.txt _files.txt.all
shuf <_files.txt.all | tail -n 200 >_files.txt

gfind . -name '*.toloka' | sed 's/^/"/'  | sed 's/$/"/' | xargs rm
python $CORPUS_PROCESS  --action process  --toloka --smart-parser-options " -v debug -max-rows 500 -adapter prod" --file-list _files.txt --output-folder documents  --smart-parser $SMART_PARSER

python create_toloka.py --document-folder $TMPFOLDER --file-list _files.txt --toloka-output toloka.tsv --toloka-golden ../../toloka/assignments/golden_1.tsv

