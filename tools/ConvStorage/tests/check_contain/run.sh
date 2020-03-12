python ../../create_json.py
[ ! -d input_files ] || rm -rf input_files

python ../../conv_storage_server.py --server-ip 127.0.0.1 --port 8080 --db-json converted_file_storage.json &
conv_server_pid=$!
disown

sha256=`sha256sum files/1501.pdf | awk '{print $1}'`
http_code=`curl -s -w '%{http_code}'  "127.0.0.1:8080?sha256=$sha256" --output 15071.docx`
kill $conv_server_pid >/dev/null
if [ $http_code == "404" ]; then
  echo "cannot get converted file"
  exit  1
fi
diff 15071.docx  files/1501.pdf.docx
