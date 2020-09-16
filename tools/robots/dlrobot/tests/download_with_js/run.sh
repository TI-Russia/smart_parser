# create a random.pdf and start pdf conversion task
PROJECT=$1

python3 ../../dlrobot.py --clear-cache-folder --project $PROJECT


files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 2 ]; then
    echo "must be 2 exported files"
    exit 1
fi

