export DECLARATOR_CONV_URL=127.0.0.1:8081

INPUT_FILE=test.pdf
[ ! -f $INPUT_FILE.docx ] || rm $INPUT_FILE.docx
cp db_input_files/f7e2614eba5c3baa2cf38cd7f1ab00c40cca0980c63a0a2a52fbf9559d5797d0.pdf $INPUT_FILE

python ../../scripts/recreate_database.py --forget-old-data
[ ! -d input_files ] || rm -rf input_files

python ../../conv_storage_server.py --db-json converted_file_storage.json &
conv_server_pid=$!
disown


sha256=`sha256sum $INPUT_FILE | awk '{print $1}'`
http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL?sha256=$sha256" --output $INPUT_FILE.docx`
kill $conv_server_pid >/dev/null
if [ $http_code == "404" ]; then
  echo "cannot get converted file"
  exit  1
fi
