PROJECT=$1
WEB_ADDR=$2
INPUT_FOLDER=input_tasks
rm -rf $INPUT_FOLDER smart_parser_cache.dbm smart_parser_cache.log

python3 ../../scripts/cloud/smart_parser_cache.py --server-address $WEB_ADDR --input-task-directory $INPUT_FOLDER &
SERVER_PID=$!
sleep 1

curl -T MainWorkPositionIncome.docx http://$WEB_ADDR
curl -T RealtyNaturalText.docx http://$WEB_ADDR

sleep 5

function check_file() {
  local filename=$1
  sha256=`sha256sum $filename | awk '{print $1}'`
  curl http://$WEB_ADDR/get_json?sha256=$sha256 > res.json
  file_size=`wc -c "res.json" | awk '{print $1}'`
  if [ $file_size -le 1000 ]; then
      echo "broken json"
      kill $SERVER_PID
      exit 1
  fi
}

check_file MainWorkPositionIncome.docx
check_file RealtyNaturalText.docx


session_write_count=`curl http://$WEB_ADDR/stats | jq  .session_write_count`
if [ $session_write_count != "2" ]; then
  echo "bad session_write_count, must be 2"
  kill $SERVER_PID
fi

kill $SERVER_PID



