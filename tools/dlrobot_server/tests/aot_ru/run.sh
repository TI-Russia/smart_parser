DUMMY=$1
export DLROBOT_CENTRAL_SERVER_ADDRESS=$2
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects
WORKER_DIR=workdir
rm -rf $RESULT_FOLDER *.log

python3 ../../dlrobot_central.py --input-folder input_projects --result-folder  ${RESULT_FOLDER}  --disable-smart-parser-cache&
CENTRAL_PID=$!
sleep 1

python3 ../../dlrobot_worker.py run_once --working-folder ${WORKER_DIR} &
WORKER_PID=$!
sleep 2

curl http://$DLROBOT_CENTRAL_SERVER_ADDRESS/stats > stats.txt
running_count=`cat stats.txt | jq '.running_count'`
if [ "$running_count" != "1" ]; then
    echo "running count must be 1"
    kill ${CENTRAL_PID}
    kill ${WORKER_PID}
    exit 1
fi

wait $WORKER_PID
result_files_count=`ls ${RESULT_FOLDER}/aot.ru.*/aot.ru.txt.click_paths | wc -l | awk '{print $1}' `
if [ "$result_files_count" != "1" ]; then
  echo "aot.ru.txt.click_paths is not sent by the worker"
  kill ${CENTRAL_PID}
  exit 1
fi

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_remote_calls.dat
if [ ! -f ${DLROBOT_RESULTS} ]; then
    kill $CENTRAL_PID
    echo "${DLROBOT_RESULTS}  does not exist (current crawl epoch (epoch 1)"
    exit 1
fi

#one more worker run for the second  crawl epoch
python3 ../../dlrobot_worker.py run_once  --working-folder ${WORKER_DIR}
if [ ! -f ${DLROBOT_RESULTS}.1 ]; then
    echo "${DLROBOT_RESULTS}.1  does not exist (crawl epoch 1)"
    kill $CENTRAL_PID
    exit 1
fi

if [ ! -f ${DLROBOT_RESULTS} ]; then
    kill $CENTRAL_PID
    echo "${DLROBOT_RESULTS}  does not exist (current crawl epoch (epoch 2))"
    exit 1
fi



kill ${CENTRAL_PID}

#restart central and read previous results
python3 ../../dlrobot_central.py --read-previous-results --input-folder input_projects --result-folder  ${RESULT_FOLDER} --disable-smart-parser-cache&
CENTRAL_PID=$!
sleep 1

curl http://$DLROBOT_CENTRAL_SERVER_ADDRESS/stats > stats.txt
input_tasks=`cat stats.txt | jq '.input_tasks'`
if [ ${input_tasks} != "0" ]; then
    echo "the previous results were not read properly"
    kill ${CENTRAL_PID}
    exit 1
fi


kill ${CENTRAL_PID}
