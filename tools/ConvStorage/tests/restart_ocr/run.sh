INPUT_FILE=../files/for_ocr.pdf 
DOCX_FILE=for_ocr.pdf.docx
rm -rf $DOCX_FILE

source ../setup_tests.sh

python ../../scripts/recreate_database.py --forget-old-data

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out --ocr-timeout 160s --disable-winword --ocr-restart-time 180s &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py ../files/freeze.pdf --conversion-timeout 200 --output-folder .

python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 180 --output-folder .

kill $conv_server_pid >/dev/null

if [ ! -f $DOCX_FILE ]; then
    echo "cannot get $DOCX_FILE after restart"
    exit 1
fi 

restart_count=`grep -c "restart ocr" db_conv.log`
if [ $restart_count == 0 ]; then
    echo "ocr was not restarted"
    exit 1
fi

