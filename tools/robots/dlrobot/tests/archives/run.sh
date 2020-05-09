PROJECT=$1
python ../../dlrobot.py --clear-cache-folder --project $PROJECT 

files_count=`/usr/bin/find result -type f | wc -l`

if [ $files_count != 4 ]; then
    echo "4 files must be exported"
    exit 1
fi

