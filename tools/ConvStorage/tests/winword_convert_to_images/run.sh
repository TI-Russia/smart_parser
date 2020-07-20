INPUT_FILE=18822_cut.pdf
[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx
source ../setup_tests.sh

python ../../scripts/recreate_database.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder pdf.ocr --ocr-output-folder  pdf.ocr.out &
conv_server_pid=$!
disown

python ../ocr_monkey.py --ocr-input-folder pdf.ocr --ocr-output-folder  pdf.ocr.out  --expecting-files-count 1 &
ocr_monkey_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 60


curl $DECLARATOR_CONV_URL/stat | jq > result_stat.json

kill $conv_server_pid >/dev/null

kill $ocr_monkey_pid >/dev/null

if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi

filesize=`stat --printf="%s" $INPUT_FILE.docx`
if [ $filesize != 21 ]; then
  echo "the size of the output file must 21 (from ocr monkey), winword converts it to a chinese doc"
  exit  1
fi

