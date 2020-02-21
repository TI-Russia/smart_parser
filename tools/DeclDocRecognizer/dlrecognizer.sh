SCRIPT_FOLDER=`dirname "$0"`
input_file=$1
output_file=$2
#soffice="/usr/bin/soffice"
soffice="C:/Program Files (x86)/LibreOffice/program/soffice.exe"
calibre_convert="C:/Program Files (x86)/Calibre2/ebook-convert.exe"
catdoc_binary="/usr/bin/catdoc"
xlsx2csv="C:/Python37/Scripts/xlsx2csv" 

which xls2csv >/dev/null
if  [ $? -ne 0 ]; then
    echo "install xls2csv from http://manpages.ubuntu.com/manpages/bionic/man1/xls2csv.1.html"
    exit 1
fi


file_extension=${input_file##*.}
filename="${input_file%.*}"

if [[ $file_extension == "xlsx" ]]; then
    python3 ${xlsx2csv} -c utf-8 -d tab  ${input_file} ${input_file}.txt
elif [[ $file_extension == "xls" ]]; then
    xls2csv -q 0 -c $'\t' -d utf-8  ${input_file} > ${input_file}.txt
    if [ $? -ne 0 ]; then
        cp $input_file $input_file.xlsx
        python3 ${xlsx2csv} -c utf-8 -d tab  ${input_file}.xlsx ${input_file}.txt
        rm $input_file.xlsx
    fi
elif [[ $file_extension == "pdf" || $file_extension == "docx"  || $file_extension == "html"  || $file_extension == "rtf" || $file_extension == "htm" ]]; then
    "$calibre_convert" $input_file  ${input_file}.txt >/dev/null
elif [[ $file_extension == "doc"  ]]; then
    $catdoc_binary -d utf-8 $input_file  > ${input_file}.txt
    if [ $? -ne 0 ]; then
        cp $input_file $input_file.docx
        "$calibre_convert" $input_file.docx  ${input_file}.txt >/dev/null
        rm $input_file.docx
    fi
else
    "$soffice" --headless --writer  --convert-to "txt:Text (encoded):UTF8" $input_file >/dev/null
     mv ${filename}.txt ${input_file}.txt
fi

if [[ ! -f ${input_file}.txt ]]; then
    echo "cannot convert $input_file"
    exit 1
fi

python3 $SCRIPT_FOLDER/dlrecognizer.py --source-file ${input_file} --txt-file ${input_file}.txt --output ${output_file}
#rm ${input_file}.txt