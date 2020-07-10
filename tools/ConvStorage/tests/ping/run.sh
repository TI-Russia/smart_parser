source ../setup_tests.sh

python ../../scripts/recreate_database.py
[ ! -d input_files ] || rm -rf input_files

python ../../conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json &
conv_server_pid=$!
disown

http_code=`curl -s -w '%{http_code}'  "$DECLARATOR_CONV_URL/ping" --output dummy.txt`


if [ $http_code != "200" ]; then
  kill $conv_server_pid >/dev/null
  echo "server did not respond properly"
  exit  1
fi


ocr_pending_all_file_size=`python ../../scripts/get_stats.py | jq '.ocr_pending_all_file_size' `
if [ "$ocr_pending_all_file_size" != 0 ]; then
  kill $conv_server_pid >/dev/null
  echo "ocr_pending_all_file_size must be 0"
  exit  1
fi

kill $conv_server_pid >/dev/null
