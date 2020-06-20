# run me in bash with "rm nohup.out; nohup bash -x run.sh&" 
cd `dirname $0`
export DECLARATOR_CONV_URL=192.168.100.152:8091
export PYTHONPATH=C:/tmp/smart_parser/smart_parser/tools
while true; do
	python C:/tmp/smart_parser/smart_parser/tools/ConvStorage/conv_storage_server.py --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json \
		--ocr-input-folder C:/tmp/conv_db/pdf.ocr --ocr-output-folder  C:/tmp/conv_db/pdf.ocr.out
	sleep 10

    #try to remove temp folders
    rm -rf input_files_cracked*

    # move log files
    mv pdf.ocr.out/*.txt ocr.logs
    mv db_conv.log db_conv.log.sav
done

