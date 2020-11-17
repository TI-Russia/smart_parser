INPUT_FILE=../files/1501.pdf
DOCX_FILE=1501.pdf.docx 
source ../setup_tests.sh

python ../../scripts/recreate_database.py  --forget-old-data

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr --disable-killing-winword &
conv_server_pid=$!
disown

function convert_file() {
    rm -rf $DOCX_FILE
    python ../../scripts/convert_pdf.py $INPUT_FILE --conversion-timeout 60 --rebuild --output-folder .
    if [ ! -f $DOCX_FILE ]; then
        kill $conv_server_pid >/dev/null
        echo "cannot get converted file"
        exit  1
    fi
}

convert_file # no rebuild, since db is empty
convert_file

deletion_count=`grep -c delete_conversion_record db_conv.log`
if [ "$deletion_count" != "1" ]; then
   kill $conv_server_pid >/dev/null
   echo "logs do not contain deletion traces"
   exit  1
fi

kill $conv_server_pid >/dev/null
