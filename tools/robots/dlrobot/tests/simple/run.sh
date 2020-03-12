rm -rf cached
python -m http.server --bind 127.0.0.1 --directory html 8090 &
web_server_pid=$!
disown

python ../../dlrobot.py --project project.txt 

kill $web_server_pid >/dev/null

files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 1 ]; then
    echo "no exported file found"
    exit 1
fi

