#не работает со всеми этим пробелами!!
#пробелы в программе /Program Files, именах вх. файлло 
#PATH="$PATH:/cygdrive/c/Program Files (x86)/LibreOffice/program/"
soff="/cygdrive/c/Program Files (x86)/LibreOffice/program/soffice.exe"
#soff="c:/Program Files (x86)/LibreOffice/program/soffice.exe"
#aliass soff="/cygdrive/c/Program Files (x86)/LibreOffice/program/soffice.exe"
args="--convert-to txt:""Text (encoded):UTF8"" --headless "

#"$soff" 01.doc

#exit


for x in *.doc*; do
    echo "$soff" "$args" $x
    "$soff" --convert-to txt:"Text (encoded):UTF8"   "$x"
    wait
done
