PROJECT=$1
python ../../dlrobot.py --project $PROJECT 

files_count=`/usr/bin/find result -type f | wc -l`

if [ $files_count != 3 ]; then
    echo "3 files must be exported"
    exit 1
fi

