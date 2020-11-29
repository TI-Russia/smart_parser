PROJECT=$1
WEB_ADDR=$2

export DLROBOT_CENTRAL_SERVER_ADDRESS=localhost:8265
export SMART_PARSER_SERVER_ADDRESS=localhost:8266
export INPUT_CENTRAl_FOLDER=input_projects
INPUT_SMART_PARSER_FOLDER=input_projects.smart_parsers
RESULT_FOLDER=processed_projects
WORKER_DIR=workdir
SMART_PARSER_DB=smart_parser_cache.dbm
rm -rf $RESULT_FOLDER *.log $INPUT_CENTRAl_FOLDER $INPUT_SMART_PARSER_FOLDER $SMART_PARSER_DB
mkdir $INPUT_CENTRAl_FOLDER
cp $PROJECT $INPUT_CENTRAl_FOLDER

python3 ../../../smart_parser_http/smart_parser_server.py --input-task-directory $INPUT_SMART_PARSER_FOLDER &
SMART_PARSER_PID=$!
sleep 1

python3 ../../dlrobot_central.py \
    --input-folder $INPUT_CENTRAl_FOLDER \
    --pdf-conversion-queue-limit 3000000000 \
    --result-folder  ${RESULT_FOLDER} &
CENTRAL_PID=$!
sleep 2


python3 ../../dlrobot_worker.py run_once --working-folder ${WORKER_DIR}

sleep 3


python3 ../../../smart_parser_http/smart_parser_client.py --action stats > stats.json
session_write_count=`cat stats.json | jq  .session_write_count`
if [ "$session_write_count" != "1" ]; then
  echo "bad session_write_count, must be 1"
  kill $CENTRAL_PID
  kill $SMART_PARSER_PID
  exit 1
fi

kill $SMART_PARSER_PID
kill $CENTRAL_PID
