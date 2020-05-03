TEST_NAME=$1
WEB_PORT=$2
WEB_IP=127.0.0.1
WEB_ADDR=$WEB_IP:$WEB_PORT
HTML_FOLDER=html
PROJECT=project.txt
PARENT_TEST_FOLDER=`pwd`

cd $TEST_NAME
TEST_FOLDER=`pwd`
[ ! -f test_log.out ] || rm test_log.out
[ ! -d cached ] || rm -rf cached
[ ! -d result ] || rm -rf result
[ ! -f $PROJECT.clicks ] || rm -rf $PROJECT.clicks
[ ! -f geckodriver.log ] || rm -rf geckodriver.log
[ ! -f dlrobot.log ] || rm -rf dlrobot.log


if [ -d $HTML_FOLDER ]; then
	curl -s --connect-timeout 4 -I $WEB_ADDR >/dev/null


	if [ $? -eq 0 ]; then
    		echo "stop other instance of http.server on $WEB_ADDR"
    		exit 1
	fi

    cd $HTML_FOLDER
	python -m http.server --bind $WEB_IP $WEB_PORT &>$TEST_FOLDER/server.log &
	WEB_SERVER_PID=$!
	disown
    cd $TEST_FOLDER
    echo "{\"sites\":[{\"morda_url\":\"http://$WEB_ADDR\"}],\"disable_search_engine\": true}"  > $PROJECT
fi

bash -x run.sh $PROJECT $WEB_ADDR &>test_log.out

if [ $? -eq 0 ]; then
     echo "$TEST_NAME succeeded"
else
     echo "$TEST_NAME failed"
     echo $TEST_NAME >> $PARENT_TEST_FOLDER/failed_tests.txt
fi

if [ -d $HTML_FOLDER ]; then
     kill $WEB_SERVER_PID >/dev/null
fi


