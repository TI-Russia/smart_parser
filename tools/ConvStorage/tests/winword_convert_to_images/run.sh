INPUT_FILE=../files/18822_cut.pdf
DOCX_FILE=18822_cut.pdf.docx
rm -rf $DOCX_FILE

source ../setup_tests.sh

python ../../scripts/recreate_database.py --forget-old-data

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder pdf.ocr --ocr-output-folder  pdf.ocr.out &
conv_server_pid=$!
disown

python ../ocr_monkey.py --ocr-input-folder pdf.ocr --ocr-output-folder  pdf.ocr.out  --expecting-files-count 1 &
ocr_monkey_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 60 --output-folder .


curl $DECLARATOR_CONV_URL/stat | jq > result_stat.json

kill $conv_server_pid >/dev/null

kill $ocr_monkey_pid >/dev/null

if [ ! -f $DOCX_FILE ]; then
  echo "cannot get converted file"
  exit  1
fi

filesize=`stat --printf="%s" $DOCX_FILE`
if [ $filesize != 21 ]; then
  echo "the size of the output file ($DOCX_FILE) must 21 (from ocr monkey), winword converts it to a chinese doc"
  exit  1
fi

