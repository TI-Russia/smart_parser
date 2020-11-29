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
[ ! -f $PROJECT.visited_pages ] || rm -rf $PROJECT.visited_pages
[ ! -f $PROJECT.click_paths ] || rm -rf $PROJECT.click_paths
[ ! -f $PROJECT.result_summary ] || rm -rf $PROJECT.result_summary
[ ! -f $PROJECT.log ] || rm -rf $PROJECT.log
[ ! -f geckodriver.log ] || rm -rf geckodriver.log


if [ -d $HTML_FOLDER ]; then
	curl -s --connect-timeout 4 -I $WEB_ADDR >/dev/null


	if [ $? -eq 0 ]; then
    		echo "stop other instance of http.server on $WEB_ADDR"
    		exit 1
	fi

    cd $HTML_FOLDER
	python3 -m http.server --bind $WEB_IP $WEB_PORT &>$TEST_FOLDER/server.log &
	WEB_SERVER_PID=$!
	disown
    cd $TEST_FOLDER
fi

echo "{\"sites\":[{\"morda_url\":\"http://$WEB_ADDR\"}],\"disable_search_engine\": true}"  > $PROJECT

/usr/bin/timeout 5m bash -x run.sh $PROJECT $WEB_ADDR &>test_log.out

if [ $? -eq 0 ]; then
     echo "$TEST_NAME succeeded"
else
     echo "$TEST_NAME failed"
     echo $TEST_NAME >> $PARENT_TEST_FOLDER/failed_tests.txt
fi

if [ -d $HTML_FOLDER ]; then
     kill $WEB_SERVER_PID >/dev/null
fi


