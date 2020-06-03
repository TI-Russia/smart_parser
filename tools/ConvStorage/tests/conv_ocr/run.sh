INPUT_FILE=a.pdf 
source ../setup_tests.sh

python ../../create_json.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
	--ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out &
conv_server_pid=$!
disown


http_code=`curl -s -w '%{http_code}' $DECLARATOR_CONV_URL/convert_if_absent/ --upload-file $INPUT_FILE --output dummy.txt`
if [ "$http_code" != "201" ]; then
  echo "cannot upload a file"
  kill $conv_server_pid >/dev/null
  exit  1
fi

was_in_ocr_queue=0
while true; do 
    sleep 3
    ls files/*.docx 2>/dev/null
    if [ $? -eq "0" ]; then
       break
    fi
    ocr_pending_all_file_size=`curl $DECLARATOR_CONV_URL/stat | jq '.ocr_pending_all_file_size'`
    if [ $ocr_pending_all_file_size > 0 ]; then
        was_in_ocr_queue=1
    fi
    http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL?sha256=$sha256" --output $INPUT_FILE.docx`
done

sleep 10 # to update json


[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx
sha256=`sha256sum $INPUT_FILE | awk '{print $1}'`
http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL?sha256=$sha256" --output $INPUT_FILE.docx`

curl $DECLARATOR_CONV_URL/stat | jq > result_stat.json


kill $conv_server_pid >/dev/null

if [ $was_in_ocr_queue != 1]; then
  echo "we did not see the input file in the ocr queue"
  exit  1
fi

git diff result_stat.json
if [ $? != 0 ]; then
  echo "stats are different"
  exit  1
fi


if [ "$http_code" == "404" ]; then
  echo "cannot get converted file, 404 returned"
  exit  1
fi

if [ ! -f $INPUT_FILE.docx ]; then
  echo "cannot get converted file"
  exit  1
fi
