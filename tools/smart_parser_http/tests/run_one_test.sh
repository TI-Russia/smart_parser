TEST_NAME=$1
WEB_PORT=$2
WEB_IP=127.0.0.1
WEB_ADDR=$WEB_IP:$WEB_PORT
HTML_FOLDER=html
PARENT_TEST_FOLDER=`pwd`

cd $TEST_NAME
TEST_FOLDER=`pwd`
[ ! -f test_log.out ] || rm test_log.out


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


