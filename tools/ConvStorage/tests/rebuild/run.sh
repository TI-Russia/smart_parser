INPUT_FILE=1501.pdf 
source ../setup_tests.sh

python ../../create_json.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr &
conv_server_pid=$!
disown

function convert_file() {
  http_code=`curl -X PUT -s -w '%{http_code}' --upload-file $INPUT_FILE --output dummy.txt $DECLARATOR_CONV_URL/convert_mandatory/` 
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


  if [ "$http_code" == "404" ]; then
    kill $conv_server_pid >/dev/null
    echo "cannot get converted file, 404 returned"
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
