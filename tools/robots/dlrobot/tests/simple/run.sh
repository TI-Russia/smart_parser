source ../setup_web_server.sh


python ../../dlrobot.py --project project.txt 

kill $WEB_SERVER_PID >/dev/null

files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 1 ]; then
    echo "no exported file found"
    exit 1
fi

