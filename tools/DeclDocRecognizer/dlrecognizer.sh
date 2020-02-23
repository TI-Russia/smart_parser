SCRIPT_FOLDER=`dirname "$0"`
input_file=$1
output_file=$2

#=============== PREREQUISITES =====================

system=`uname -s`
if [[ $system == CYGWIN* ]]; then
    SOFFICE_BINARY="C:/Program Files (x86)/LibreOffice/program/soffice.exe"
    CALLIBRE_CONVERT="C:/Program Files (x86)/Calibre2/ebook-convert.exe"
    OFFICE_2_TXT=$SCRIPT_FOLDER"/../Office2Txt/bin/Release/netcoreapp3.1/Office2Txt.exe"

else
    SOFFICE_BINARY=`which soffice`
    if [ $? -ne 0 ]; then
        echo "cannot find soffice, install libreoffice"
        exit 1
    fi

    CALLIBRE_CONVERT=`which ebook-convert`
    if [ $? -ne 0 ]; then
        echo "cannot find callibre, sudo apt install calibre"
        exit 1
    fi
    OFFICE_2_TXT=$SCRIPT_FOLDER"/../Office2Txt/bin/Release/netcoreapp3.1/Office2Txt"                                                                                            
fi
                          
CATDOC_BINARY=`which catdoc`
if  [ $? -ne 0 ]; then
    echo "install catdoc \n sudo apt install catdoc"
    exit 1
fi

XLS_2_CSV=`which xls2csv`
if  [ $? -ne 0 ]; then
    echo "install xls2csv from http://manpages.ubuntu.com/manpages/bionic/man1/xls2csv.1.html"
    exit 1
fi

pip3 show xlsx2csv >/dev/null
if  [ $? -ne 0 ]; then
    echo "install xlsx2csv \n pip3 install xlsx2csv"
    exit 1
fi
if [[ $system == CYGWIN* ]]; then
    XLSX_2_CSV="C:/Python37/Scripts/xlsx2csv"
else
    XLSX_2_CSV=`which xlsx2csv` 
fi

if [ ! -f $OFFICE_2_TXT ]; then 
    echo "build ../Office2Txt:\n dotnet build -c Release ../tools/Office2Txt"
    exit 1
fi

############### THE MAIN PROCESS ========================


file_extension=${input_file##*.}
filename="${input_file%.*}"

if [[ $file_extension == "xlsx" ]]; then
    python3 ${XLSX_2_CSV} -c utf-8 -d tab  ${input_file} ${input_file}.txt
elif [[ $file_extension == "xls" ]]; then
    $XLS_2_CSV -q 0 -c $'\t' -d utf-8  ${input_file} > ${input_file}.txt
    if [ $? -ne 0 ]; then
        cp $input_file $input_file.xlsx
        python3 ${XLSX_2_CSV} -c utf-8 -d tab  ${input_file}.xlsx ${input_file}.txt
        rm $input_file.xlsx
    fi
elif [[ $file_extension == "docx" ]]; then

    $OFFICE_2_TXT $input_file  ${input_file}.txt # can be  huge, soffice and callibre cannot process huge files

elif [[ $file_extension == "pdf" || $file_extension == "html"  || $file_extension == "rtf" || $file_extension == "htm" ]]; then

    /usr/bin/timeout 30m "$CALLIBRE_CONVERT" $input_file  ${input_file}.txt >/dev/null 2>/dev/null

elif [[ $file_extension == "doc"  ]]; then
    $CATDOC_BINARY -d utf-8 $input_file  > ${input_file}.txt
    if [ $? -ne 0 ]; then
        cp $input_file $input_file.docx
        $OFFICE_2_TXT $input_file.docx  ${input_file}.txt 
        rm $input_file.docx
    fi
else
    /usr/bin/timeout 30m "$SOFFICE_BINARY" --headless --writer  --convert-to "txt:Text (encoded):UTF8" $input_file >/dev/null
     mv ${filename}.txt ${input_file}.txt
fi

if [[ ! -f ${input_file}.txt ]]; then
    echo "cannot convert $input_file"
    #may be unknown_result?
    echo '{"result":"some_other_document_result", "description": "cannot parse document"}' | jq  > ${output_file}
    exit 1
fi

python3 $SCRIPT_FOLDER/dlrecognizer.py --source-file ${input_file} --txt-file ${input_file}.txt --output ${output_file}
rm ${input_file}.txt