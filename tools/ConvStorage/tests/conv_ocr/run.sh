INPUT_FILE=a.pdf 

[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx

source ../setup_tests.sh

python ../../scripts/recreate_database.py

python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out --disable-killing-winword &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion_timeout 180


curl $DECLARATOR_CONV_URL/stat | jq > result_stat.json

kill $conv_server_pid >/dev/null

if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi


git diff --exit-code result_stat.json
if [ $? != 0 ]; then
  echo "stats are different"
  exit  1
fi


