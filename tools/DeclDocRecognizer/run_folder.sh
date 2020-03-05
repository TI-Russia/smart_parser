SCRIPT_FOLDER=`dirname "$0"`
SCRIPT_FOLDER=`realpath $SCRIPT_FOLDER` 
cd  $1
rm *.json
rm *.txt

ls | xargs  --verbose -I '{}' -n 1 -P 5  \
   sh -c "bash  $SCRIPT_FOLDER/dlrecognizer.sh \"\$1\" \"\$1\".json "  -- {}  

cd -
