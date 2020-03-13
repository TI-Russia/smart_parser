python ../../create_json.py
[ ! -d input_files ] || rm -rf input_files

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json &
conv_server_pid=$!
disown

http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL/ping" --output dummy.txt`
kill $conv_server_pid >/dev/null
if [ $http_code != "200" ]; then
  echo "server did not respond properly"
  exit  1
fi
