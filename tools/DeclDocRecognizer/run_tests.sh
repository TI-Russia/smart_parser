SCRIPT_FOLDER=`dirname "$0"`
system=`uname -s`

#=================
pip3 show xlsx2csv >/dev/null
if  [ $? -ne 0 ]; then
    echo -e "install xlsx2csv\npip3 install xlsx2csv"
    exit 1
fi
if [[ $system == CYGWIN* ]]; then
    python_path=`where python | head -n 1`
    python_path=`dirname $python_path`
    XLSX_2_CSV="$python_path/Scripts/xlsx2csv"
else
    XLSX_2_CSV=`which xlsx2csv` 
fi

if  [ ! -f $XLSX_2_CSV ]; then
    echo "cannot find xlsx2csv"
    exit 1

fi
#===================
CATDOC_BINARY=`which catdoc`
if  [ $? -ne 0 ]; then
    echo "install catdoc \n sudo apt install catdoc"
    exit 1
fi

#===================
XLS_2_CSV=`which xls2csv`
if  [ $? -ne 0 ]; then
    echo "install xls2csv from http://manpages.ubuntu.com/manpages/bionic/man1/xls2csv.1.html"
    exit 1
fi

if [[ $system == CYGWIN* ]]; then
    SOFFICE_BINARY="C:/Program Files (x86)/LibreOffice/program/soffice.exe"
    if [ ! -f "$SOFFICE_BINARY" ]; then
        echo "cannot find libreoffice, install libreoffice"
        exit 1
    fi

    CALLIBRE_CONVERT="C:/Program Files (x86)/Calibre2/ebook-convert.exe"
    if [ ! -f "$CALLIBRE_CONVERT" ]; then
        echo "cannot find callibre, install calibre"
        exit 1
    fi
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

if [ ! -f $OFFICE_2_TXT ]; then 
    echo -e "build ../Office2Txt:\ndotnet build -c Release ../tools/Office2Txt"
    exit 1
fi

#===================================
cd  tests
rm *.json

for x in `ls * | grep -v json`; do
    bash ../dlrecognizer.sh $x  $x.json
done
cd -
git diff tests
