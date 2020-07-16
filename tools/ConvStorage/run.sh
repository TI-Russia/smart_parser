# run me in bash with "rm nohup.out; nohup bash -x run.sh&" 
cd `dirname $0`
export DECLARATOR_CONV_URL=192.168.100.152:8091
export PYTHONPATH=C:/tmp/smart_parser/smart_parser/tools
process_count=`wmic process list  full  | tr -d '\r' | grep  conv_storage_server.py | grep -v grep | wc -l`
if [ $process_count == 0 ]; then
    #try to remove temp folders
    rm -rf input_files_cracked*

    # move log files
    mv db_conv.log db_conv.log.sav

	nohup python C:/tmp/smart_parser/smart_parser/tools/ConvStorage/conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
		--ocr-input-folder C:/tmp/conv_db/pdf.ocr --ocr-output-folder  C:/tmp/conv_db/pdf.ocr.out &
fi

