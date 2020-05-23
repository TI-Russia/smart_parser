program=../bin/Debug/MicrosoftPdf2Docx.exe 

for x in positive/*.pdf; do
    [ ! -f $x.docx ] || rm $x.docx
    $program $x
    if [ ! -f $x.docx ]; then
        echo "fail on positive $x"
        exit 1
    fi
done

for x in negative/*.pdf; do
    [ ! -f $x.docx ] || rm $x.docx
    $program $x
    if [ -f $x.docx ]; then
        echo "fail on negative $x"
        exit 1
    fi
done

echo "success"