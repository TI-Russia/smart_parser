PROJECT=$1
WEB_ADDR=$2

INPUT_FOLDER=input_tasks
rm -rf $INPUT_FOLDER smart_parser_cache.dbm smart_parser_cache.log

python3 ../../scripts/cloud/smart_parser_cache.py --server-address $WEB_ADDR --input-task-directory $INPUT_FOLDER &
SERVER_PID=$!
sleep 1
sha256=`sha256sum MainWorkPositionIncome.docx | awk '{print $1}'`

not_found=`curl -s -o /dev/null   -w "%{http_code}" http://$WEB_ADDR/get_json?sha256=$sha256`
if [ $not_found != "404" ]; then
  echo "dbm is not empty or server failed to answer properly"
  kill $SERVER_PID
fi



curl -T MainWorkPositionIncome.docx http://$WEB_ADDR
if [ $? != 0 ]; then
  echo "put file failed"
  kill $SERVER_PID
fi
sleep 5
sha256=`sha256sum MainWorkPositionIncome.docx | awk '{print $1}'`

curl http://$WEB_ADDR/get_json?sha256=$sha256 > res.json
file_size=`wc -c "res.json" | awk '{print $1}'`
if [ $file_size -le 1000 ]; then
  echo "broken json"
  kill $SERVER_PID
fi

ping_answer=`curl http://$WEB_ADDR/ping`
if [ $ping_answer != "pong" ]; then
  echo "bad ping answer"
  kill $SERVER_PID
fi


session_write_count=`curl http://$WEB_ADDR/stats | jq  .session_write_count`
if [ $session_write_count != "1" ]; then
  echo "bad session_write_count, must be 1"
  kill $SERVER_PID
fi

kill $SERVER_PID



