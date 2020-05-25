INPUT_FILE=1501.pdf 
[ ! -f 1501.pdf.docx ] || rm  1501.pdf.docx
source ../setup_tests.sh
python ../../create_json.py
python ../../conv_storage_server.py --clear-json --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr &
conv_server_pid=$!
disown
sleep 2
python ../../scripts/convert_pdf.py  $INPUT_FILE
kill $conv_server_pid >/dev/null
if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi

