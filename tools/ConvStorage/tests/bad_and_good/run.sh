INPUT_FILE=../files/good.pdf
DOCX_FILE=good.pdf.docx  
[ ! -f $DOCX_FILE ] || rm $DOCX_FILE
[ ! -f convert_pdf.log ] || rm  convert_pdf.log
                                               
source ../setup_tests.sh

python ../../scripts/recreate_database.py --forget-old-data

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out --ocr-logs-folder  ../ocr.logs --disable-killing-winword &
conv_server_pid=$!
disown

python ../../scripts/convert_pdf.py $INPUT_FILE ../files/bad.pdf --conversion-timeout 180 --output-folder .

if [ $? -eq 0 ]; then
    echo "convert_pdf.py must fail on ../files/bad.pdf"    
    kill $conv_server_pid >/dev/null
    exit  1
fi

curl $DECLARATOR_CONV_URL/stat | jq > result_stat.json

kill $conv_server_pid >/dev/null

git diff --exit-code result_stat.json
if [ $? != 0 ]; then
  echo "stats are different"
  exit  1
fi


if [ ! -f $DOCX_FILE ]; then
  echo "cannot get converted file"
  exit  1
fi

