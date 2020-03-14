rm -rf cached
WEB_IP=127.0.0.1
WEB_PORT=8090
WEB_ADDR=$WEB_IP:$WEB_PORT

curl --connect-timeout 4 -I $WEB_ADDR 2>/dev/null

if [ $? -eq 0 ]; then
    echo "stop other instance of http.server on $WEB_ADDR"
    exit 1
fi
taskkill /F  /IM firefox.exe

python -m http.server --bind $WEB_IP --directory html $WEB_PORT &
WEB_SERVER_PID=$!
disown

[ ! -f project.txt.clicks ] || rm -rf project.txt.clicks