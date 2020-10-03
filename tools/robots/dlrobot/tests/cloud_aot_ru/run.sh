DUMMY=$1
WEB_ADDR=$2
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects
WORKER_DIR=workdir
rm -rf $RESULT_FOLDER *.log

python3 ../../scripts/cloud/dlrobot_central.py --server-address ${WEB_ADDR} --input-folder input_projects --result-folder  ${RESULT_FOLDER} &
CENTRAL_PID=$!
sleep 1

python3 ../../scripts/cloud/dlrobot_worker.py run_once --server-address ${WEB_ADDR} --working-folder ${WORKER_DIR} &
WORKER_PID=$!
sleep 2

curl http://$WEB_ADDR/stats > stats.txt
running_count=`cat stats.txt | jq '.running_count'`
if [ "$running_count" != "1" ]; then
    echo "running count must be 1"
    kill ${CENTRAL_PID}
    kill ${WORKER_PID}
    exit 1
fi

wait $WORKER_PID

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_remote_calls.dat

function run_worker() {
  local expected_lines=$1
  python3 ../../scripts/cloud/dlrobot_worker.py run_once --server-address ${WEB_ADDR} --working-folder ${WORKER_DIR}
  number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}'`
  if [ ${number_projects} != $expected_lines ]; then
      echo "${DLROBOT_RESULTS} is not updated properly"
      kill ${CENTRAL_PID}
      exit 1
  fi
}
run_worker 1
#one more worker run, but there are no jobs
run_worker 1

if [ ! -f ${RESULT_FOLDER}/aot.ru/aot.ru.txt.click_paths ]; then
  echo "aot.ru.txt.click_paths is not sent by the worker"
  kill ${CENTRAL_PID}
  exit 1
fi

kill ${CENTRAL_PID}

#restart central and read previous results
python3 ../../scripts/cloud/dlrobot_central.py --read-previous-results --server-address ${WEB_ADDR} --input-folder input_projects --result-folder  ${RESULT_FOLDER} &
CENTRAL_PID=$!
sleep 1
run_worker 1
kill ${CENTRAL_PID}
