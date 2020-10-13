PROJECT=$1
export SMART_PARSER_SERVER_ADDRESS=$2

INPUT_FOLDER=input_tasks
  rm -rf $INPUT_FOLDER smart_parser_cache.dbm smart_parser_cache.log

python3 ../../scripts/cloud/smart_parser_cache.py --input-task-directory $INPUT_FOLDER &
SERVER_PID=$!
sleep 2

not_found=`python3 ../../scripts/cloud/smart_parser_cache_client.py --action get MainWorkPositionIncome.docx`
if [ "$not_found" != "not found" ]; then
  echo "dbm is not empty or server failed to answer properly"
  kill $SERVER_PID
  exit 1
fi

python3 ../../scripts/cloud/smart_parser_cache_client.py --action put MainWorkPositionIncome.docx
if [ $? != 0 ]; then
  echo "put file failed"
  kill $SERVER_PID
  exit 1
fi
sleep 5

python3 ../../scripts/cloud/smart_parser_cache_client.py --action get MainWorkPositionIncome.docx > res.json

file_size=`wc -c "res.json" | awk '{print $1}'`
if [ $file_size -le 1000 ]; then
  echo "broken json"
  kill $SERVER_PID
  exit 1
fi

ping_answer=`curl http://$SMART_PARSER_SERVER_ADDRESS/ping`
if [ $ping_answer != "pong" ]; then
  echo "bad ping answer"
  kill $SERVER_PID
  exit 1
fi


session_write_count=`python3 ../../scripts/cloud/smart_parser_cache_client.py --action stats | jq  .session_write_count`
if [ "$session_write_count"  != "1" ]; then
  echo "bad session_write_count, must be 1"
  kill $SERVER_PID
  exit 1
fi

kill $SERVER_PID



