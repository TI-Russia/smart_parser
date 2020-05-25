INPUT_FILE=good.pdf 
source ../setup_tests.sh

python ../../create_json.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out --ocr-logs-folder  ../ocr.logs &
conv_server_pid=$!
disown



http_code=`curl -s -w '%{http_code}' $DECLARATOR_CONV_URL/convert_if_absent/ --upload-file bad.pdf --output dummy.txt`
if [ "$http_code" != "201" ]; then
  echo "cannot upload a file"
  kill $conv_server_pid >/dev/null
  exit  1
fi

http_code=`curl -s -w '%{http_code}' $DECLARATOR_CONV_URL/convert_if_absent/ --upload-file good.pdf --output dummy.txt`
if [ "$http_code" != "201" ]; then
  echo "cannot upload a file"
  kill $conv_server_pid >/dev/null
  exit  1
fi


while true; do 
    sleep 10
    ls files/*.docx 2>/dev/null
    if [ $? -eq "0" ]; then
       break
    fi
done


sleep 10 # to update json


[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx
sha256=`sha256sum $INPUT_FILE | awk '{print $1}'`
http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL?sha256=$sha256" --output $INPUT_FILE.docx`


#wait ocr files processed
while true; do 
    files_count=`ls ../pdf.ocr/*.pdf | wc -l`
    if [ "$files_count" == "0" ]; then
       break
    fi
    sleep 10
done

kill $conv_server_pid >/dev/null

if [ "$http_code" == "404" ]; then
  echo "cannot get converted file, 404 returned"
  exit  1
fi

if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi

