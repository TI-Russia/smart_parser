DUMMY=$1
export SMART_PARSER_SERVER_ADDRESS=$2
INPUT_FOLDER=input_tasks
rm -rf $INPUT_FOLDER smart_parser_cache.dbm *.log

python3 ../../scripts/cloud/smart_parser_cache.py --input-task-directory $INPUT_FOLDER &
SERVER_PID=$!
sleep 1

python3 ../../scripts/cloud/smart_parser_cache_client.py --action put MainWorkPositionIncome.docx
python3 ../../scripts/cloud/smart_parser_cache_client.py --action put RealtyNaturalText.docx

sleep 5

function check_file() {
  local filename=$1
  python3 ../../scripts/cloud/smart_parser_cache_client.py --action get $filename > res.json
  file_size=`wc -c "res.json" | awk '{print $1}'`
  if [ $file_size -le 1000 ]; then
      echo "broken json"
      kill $SERVER_PID
      exit 1
  fi
}

check_file MainWorkPositionIncome.docx
check_file RealtyNaturalText.docx


session_write_count=`python3 ../../scripts/cloud/smart_parser_cache_client.py --action stats | jq  .session_write_count`
if [ $session_write_count != "2" ]; then
  echo "bad session_write_count, must be 2"
  kill $SERVER_PID
fi

kill $SERVER_PID



