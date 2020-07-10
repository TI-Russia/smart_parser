program=../bin/Debug/MicrosoftPdf2Docx.exe 

rm -rf positive/*.pdf.docx negative/*.pdf.docx >/dev/null
$program positive/*.pdf negative/*.pdf

for x in positive/*.pdf; do
    if [ ! -f $x.docx ]; then
        echo "fail on positive $x"
        exit 1
    fi
done

for x in negative/*.pdf; do
    if [ -f $x.docx ]; then
        echo "fail on negative $x"
        exit 1
    fi
done

echo "success"