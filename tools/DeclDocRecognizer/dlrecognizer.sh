SCRIPT_FOLDER=`dirname "$0"`
input_file=$1
output_file=$2
#soffice="/usr/bin/soffice"
soffice="C:/Program Files (x86)/LibreOffice/program/soffice.exe"
calibre_convert="C:/Program Files (x86)/Calibre2/ebook-convert.exe"

file_extension=${input_file##*.}
filename="${input_file%.*}"

#echo "file extension: $file_extension"

if [[ $file_extension == "xlsx" || $file_extension == "xls" ]]; then
    # 32 is field delimeter
    # 76 is utf
    "$soffice" --headless  --convert-to csv:"Text - txt - csv (StarCalc)":32,,76 $input_file  >/dev/null
    mv ${filename}.csv ${input_file}.txt
elif [[ $file_extension == "pdf" ]]; then
    "$calibre_convert" $input_file  ${input_file}.txt >/dev/null
else
    #"$soffice" --headless --writer  --convert-to txt $input_file
    "$soffice" --headless --writer  --convert-to "txt:Text (encoded):UTF8" $input_file >/dev/null
    mv ${filename}.txt ${input_file}.txt
fi

if [[ ! -f ${input_file}.txt ]]; then
    echo "cannot convert $input_file"
    exit 1
fi

python3 $SCRIPT_FOLDER/dlrecognizer.py --input ${input_file}.txt --output ${output_file}
rm ${input_file}.txt