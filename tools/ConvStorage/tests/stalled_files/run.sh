INPUT_FILE=a.pdf 
source ../setup_tests.sh

python ../../create_json.py

#this ocr-input-folder is not watched
python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder pdf.ocr --ocr-output-folder  pdf.ocr.out --ocr-timeout 5s &
conv_server_pid=$!
disown


http_code=`curl -s -w '%{http_code}' $DECLARATOR_CONV_URL/convert_if_absent/ --upload-file $INPUT_FILE --output dummy.txt`
if [ "$http_code" != "201" ]; then
  echo "cannot upload a file"
  kill $conv_server_pid >/dev/null
  exit  1
fi

sleep 1m

kill $conv_server_pid >/dev/null

files_count=`ls pdf.ocr | wc -l`
if [ $files_count  != 0 ];then
  echo "orphan files were not deleted"
  exit 1
fi


