INPUT_FILE=1501.pdf 
[ ! -f 1501.pdf.docx ] || rm  1501.pdf.docx
source ../setup_tests.sh
python ../../scripts/recreate_database.py
python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr --disable-killing-winword &
conv_server_pid=$!
disown
sleep 2
python ../../scripts/convert_pdf.py  $INPUT_FILE
if [ $? != "0" ]; then
  echo "convert_pdf return non-zero exit code on $INPUT_FILE"
  kill $conv_server_pid >/dev/null
  exit  1
fi
if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file $INPUT_FILE.docx"
  kill $conv_server_pid >/dev/null
  exit  1
fi

rm -rf convert_pdf.log
BROKEN_PDF=broken.pdf
python ../../scripts/convert_pdf.py  $BROKEN_PDF
if [ $? == "0" ]; then
  echo "convert_pdf return zero exit code on $BROKEN_PDF"
  kill $conv_server_pid >/dev/null 
  exit  1
fi

lines_count=`grep 'register conversion task' convert_pdf.log | wc -l`
if [ $lines_count != 0 ]; then
  echo "$BROKEN_PDF should not even be sent to server"
  kill $conv_server_pid >/dev/null 
  exit  1
fi

kill $conv_server_pid >/dev/null


