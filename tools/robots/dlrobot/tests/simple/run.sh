PROJECT=$1
RESULT_FOLDER=result
rm -rf $RESULT_FOLDER *.log
python3 ../../dlrobot.py --clear-cache-folder --project $PROJECT

files_count=`/usr/bin/find $RESULT_FOLDER -type f |  wc -l`
if [ $files_count != 1 ]; then
    echo "must be 1 exported file"
    exit 1
fi

