cd $1
rm -rf *.json *.log *.stdout 2>/dev/null
for x in `ls *.docx *.doc *.pdf *.htm *.html *.rtf *.xls *.xlsx 2>/dev/null`; do 
  /usr/bin/timeout 30m /home/sokirko/smart_parser/src/bin/Release/netcoreapp3.1/smart_parser -decimal-raw-normalization $x >$x.stdout
done
rm smart_parser*log
rm main.txt
rm second.txt
cd -