INPUT_FILE=../files/1501.pdf
DOCX_FILE=1501.pdf.docx
rm -rf 1501.pdf.docx
source ../setup_tests.sh
python ../../scripts/recreate_database.py --forget-old-data
python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-winword --disable-killing-winword &
conv_server_pid=$!
disown
sleep 2
python ../../scripts/convert_pdf.py  $INPUT_FILE --conversion-timeout 1 --output-folder . 2>convert_pdf.log
if [ $? == "0" ]; then
  echo "convert_pdf return zero exit code on $INPUT_FILE while --conversion-timeout 1 is specified"
  kill $conv_server_pid >/dev/null
  exit  1
fi

kill $conv_server_pid >/dev/null


