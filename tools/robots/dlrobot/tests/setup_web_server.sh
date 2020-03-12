rm -rf cached
curl --connect-timeout 10 -I 127.0.0.1:8090 2>/dev/null

if [ $? -eq 0 ]; then
    echo "stop other instance of http.server on 127.0.0.1:8090"
    exit 1
fi
taskkill /F  /IM firefox.exe

python -m http.server --bind 127.0.0.1 --directory html 8090 &
WEB_SERVER_PID=$!
disown
