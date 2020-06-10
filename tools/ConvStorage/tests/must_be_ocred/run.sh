rm *.pdf.docx 2> /dev/null
source ../setup_tests.sh
python ../../scripts/recreate_database.py
python ../../conv_storage_server.py --clear-db --server-address $DECLARATOR_CONV_URL --db-json converted_file_storage.json --ocr-input-folder ../pdf.ocr --ocr-output-folder  ../pdf.ocr.out &
conv_server_pid=$!
disown
sleep 2
python ../../scripts/convert_pdf.py  *.pdf
kill $conv_server_pid >/dev/null
for pdf in *.pdf; do 
    docx=$pdf.docx
	if [ ! -f $docx ]; then
  		echo "cannot found converted file $docx"
  		exit  1
	fi
    filesize=`stat --printf="%s" $docx`
    if [ $filesize -ge 20000 ]; then
        echo "the size of the output file $docx must be less than 20000 (from Finereader), winword converts it to a jpeg"
        exit  1
    fi
done

