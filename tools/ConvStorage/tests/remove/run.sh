INPUT_FILE=1501.pdf 
source ../setup_tests.sh

python ../../create_json.py

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --disable-ocr &
conv_server_pid=$!
disown



http_code=`curl -s -w '%{http_code}' $DECLARATOR_CONV_URL --upload-file $INPUT_FILE --output dummy.txt`
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

http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL?sha256=$sha256&delete_file=1"`

if [ "$http_code" == "404" ]; then
  kill $conv_server_pid >/dev/null
  echo "cannot delete file"
  exit  1
fi

files_count=`ls files | wc -l`
if [ "$files_count" != "0" ]; then
   kill $conv_server_pid >/dev/null
   echo "the file was not deleted"
   exit  1
fi



kill $conv_server_pid >/dev/null
