INPUT_FILE=1501.pdf
[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx
source ../setup_tests.sh

python ../../scripts/recreate_database.py --forget-old-data

python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr  --disable-killing-winword &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 60

kill $conv_server_pid >/dev/null

if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi

