source ../setup_web_server.sh


python ../../dlrobot.py --project project.txt 

kill $WEB_SERVER_PID >/dev/null

files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 3 ]; then
    echo "3 files must be exported"
    exit 1
fi

