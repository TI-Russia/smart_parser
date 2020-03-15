TEST_FOLDER=`dirname "${BASH_SOURCE[0]}"`
export DECLARATOR_CONV_URL=127.0.0.1:8081

pdf_ocr=`realpath $TEST_FOLDER/pdf.ocr`
pdf_ocr_out=`realpath $TEST_FOLDER/pdf.ocr.out`
if [ ! -d $pdf_ocr ]; then
    echo "run python update_finereader_task.py, and upload test.hft to finreader hot folder"
    exit 1
fi
if [ ! -d $pdf_ocr_out ]; then
    echo "run python update_finereader_task.py, and upload test.hft to finreader hot folder"
    exit 1
fi

hotfolders_count=`tasklist | grep -c HotFolder`
if [ $hotfolders_count == "0" ]; then
   echo "run Abbyy HotFolder and import test.hft"
fi

[ ! -d input_files ] || rm -rf input_files
[ ! -d input_files_cracked ] || rm -rf input_files_cracked
[ ! -d files ] || rm -rf files
[ ! -f db_conv.log ] || rm  db_conv.log
if [ -f db_conv.log ]; then
  echo "cannot remove db_conv.log"
  exit  1
fi
rm -rf $pdf_ocr/*
rm -rf $pdf_ocr_out/*

ping_conv_server=`curl --connect-timeout 3 $DECLARATOR_CONV_URL/ping`
if [ "$ping_conv_server" == "yes" ]; then
  echo "stop other instances of conversion servers"
  exit 1
fi

