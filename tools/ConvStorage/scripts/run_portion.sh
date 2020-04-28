# run this script under  windows (cygwin)
CONV=C:/tmp/smart_parser/smart_parser/tools/MicrosoftPdf2Docx/bin/Debug/MicrosoftPdf2Docx.exe
if [[ ! -f $CONV ]]; then 
    echo "cannot find $CONV"
    exit 1
fi
taskkill.exe  /f /IM winword.exe
taskkill.exe  /f /IM pdfreflow.exe

#Microsoft PDF reader is multithreaded do not use max_cpu here 
# Got  RPC_E_SERVERCALL_RETRYLATER for  Office 2016 under  windows 7 so I have to  run only one instance 
#  MicrosoftPdf2Docx.exe at a time

ls pdf.winword/*.pdf  > pdf_list.txt
rm portion_pdf*
split -l 100 pdf_list.txt portion_pdf
for x in  portion_pdf*; do
    cat $x  | xargs --verbose -n 1  /usr/bin/timeout 10m $CONV 
    sleep 20s
    taskkill.exe  /f /IM winword.exe
    taskkill.exe  /f /IM pdfreflow.exe
done
rm portion_pdf*

if [[ -f failed ]]; then
    rm -rf failed 
fi
mkdir failed
for pdf in pdf.winword/*.pdf; do
    docx="$pdf.docx"
    if [[ ! -f $docx ]]; then
        mv $pdf failed
    fi
done

# run finereader ocr on folder failed!

