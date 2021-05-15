# run me in bash with 
# cd /cygdrive/c/tmp/conv_db; rm nohup.out; nohup bash -x start_server.sh&; 
# disown $!

cd `dirname $0`
export DECLARATOR_CONV_URL=192.168.100.152:8091
export PYTHONPATH=C:/tmp/smart_parser/smart_parser/tools
while True; do
  nice --10 python C:/tmp/smart_parser/smart_parser/tools/ConvStorage/conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
		--ocr-input-folder C:/tmp/conv_db/pdf.ocr --ocr-output-folder  C:/tmp/conv_db/pdf.ocr.out

  date
  echo "restart conv_storage_server.py"
done