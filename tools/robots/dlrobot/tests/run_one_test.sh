TEST_FOLDER=$1
WEB_PORT=$2
WEB_IP=127.0.0.1
WEB_ADDR=$WEB_IP:$WEB_PORT
HTML_FOLDER=html
PROJECT=project.txt
cd $TEST_FOLDER

[ ! -f test_log.out ] || rm test_log.out
[ ! -d cached ] || rm -rf cached
[ ! -d result ] || rm -rf result
[ ! -f $PROJECT.clicks ] || rm -rf $PROJECT.clicks
[ ! -f geckodriver.log ] || rm -rf geckodriver.log
[ ! -f dlrobot.log ] || rm -rf dlrobot.log



if [ -d $HTML_FOLDER ]; then
	curl --connect-timeout 4 -I $WEB_ADDR 2>/dev/null

	if [ $? -eq 0 ]; then
    		echo "stop other instance of http.server on $WEB_ADDR"
    		exit 1
	fi

    cd $HTML_FOLDER
	python -m http.server --bind $WEB_IP $WEB_PORT 1>&2 2> $TEST_FOLDER/server.log &
	WEB_SERVER_PID=$!
	disown
    cd -

    echo "{\"sites\":[{\"morda_url\":\"http://$WEB_ADDR\"}],\"disable_search_engine\": true}"  > $PROJECT
fi

bash -x run.sh $PROJECT $WEB_ADDR >test_log.out 2>&1
#bash -x run.sh $PROJECT

if [ $? -eq 0 ]; then
     echo "$TEST_FOLDER succeeded"
else
     echo "$TEST_FOLDER failed"
fi

if [ -d $HTML_FOLDER ]; then
     kill $WEB_SERVER_PID >/dev/null
fi


