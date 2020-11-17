INPUT_FILE=../files/1501.pdf
DOCX_FILE=1501.pdf.docx
rm -rf $INPUT_FILE.docx

source ../setup_tests.sh

python ../../scripts/recreate_database.py --forget-old-data

python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr  --disable-killing-winword &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 60 --output-folder .

kill $conv_server_pid >/dev/null

if [ ! -f $DOCX_FILE ]; then
  echo "cannot get converted file"
  exit  1
fi

rm $DOCX_FILE

