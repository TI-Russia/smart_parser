rm good.pdf.docx
source ../setup_tests.sh

python ../../scripts/recreate_database.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out --ocr-timeout 160s --disable-winword --ocr-restart-time 180s &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py freeze.pdf --conversion-timeout 200

python ../../scripts/convert_pdf.py good.pdf --conversion-timeout 180

kill $conv_server_pid >/dev/null

if [ ! -f good.pdf.docx ]; then
    echo "cannot get good file after restart"
    exit 1
fi 

restart_count=`grep -c "restart ocr" db_conv.log`
if [ $restart_count == 0 ]; then
    echo "ocr was not restarted"
    exit 1
fi

