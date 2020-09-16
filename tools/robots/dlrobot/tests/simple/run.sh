PROJECT=$1

python3 ../../dlrobot.py --clear-cache-folder --project $PROJECT

files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 1 ]; then
    echo "no exported file found"
    exit 1
fi

