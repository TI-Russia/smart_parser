# run me in bash with 
# cd /cygdrive/c/tmp/conv_db; rm nohup.out; nohup bash -x start_server.sh&; 
# disown $!

cd `dirname $0`
export DECLARATOR_CONV_URL=192.168.100.152:8091
export TOOLS=c:/tmp/smart_parser/smart_parser/tools
export PYTHONPATH=$TOOLS
export PYTHON=C:/Users/sokir/AppData/Local/Microsoft/WindowsApps/python.exe


while True; do
  nice --20 $PYTHON $TOOLS/ConvStorage/conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
		--ocr-input-folder c:/tmp/conv_db/pdf.ocr --ocr-output-folder  c:/tmp/conv_db/pdf.ocr.out

  date
  echo "restart conv_storage_server.py"
done