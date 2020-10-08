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

python3 ../../scripts/cloud/dlrobot_central.py --input-folder $INPUT_CENTRAl_FOLDER --result-folder  ${RESULT_FOLDER} &
CENTRAL_PID=$!
sleep 1

python3 ../../scripts/cloud/smart_parser_cache.py --input-task-directory $INPUT_SMART_PARSER_FOLDER &
SMART_PARSER_PID=$!
sleep 1

python3 ../../scripts/cloud/dlrobot_worker.py run_once --working-folder ${WORKER_DIR}

kill $SMART_PARSER_PID
kill $CENTRAL_PID

sleep 3

file_size=`wc -c $SMART_PARSER_DB | awk '{print $1}'`
if [ $file_size -le 1000 ]; then
  echo "broken smart parser json"
fi

