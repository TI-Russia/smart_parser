PROJECT=$1
python ../../dlrobot.py --project $PROJECT

files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 1 ]; then
    echo "no exported file found"
    exit 1
fi

kazan_link=`grep -c "add link.*kazantcevo'`
if [ $kazan_link != 0 ]; then
    echo "must be no link to kazantcevo"
    exit 1
fi
