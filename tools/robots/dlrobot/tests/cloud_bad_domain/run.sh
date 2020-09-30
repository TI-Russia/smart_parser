DUMMY=$1
WEB_ADDR=$2
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects
WORKER_DIR=worker

rm -rf $RESULT_FOLDER


python3 ../../scripts/cloud/dlrobot_central.py --retries-count 2 --server-address ${WEB_ADDR} --input-folder input_projects --result-folder  ${RESULT_FOLDER} &
WEB_SERVER_PID=$!
sleep 1

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_remote_calls.dat

function run_worker() {
  local expected_lines=$1
  python3 ../../scripts/cloud/dlrobot_worker.py run_once --server-address ${WEB_ADDR} --tmp-folder ${WORKER_DIR}
  number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}'`
  if [ ${number_projects} != $expected_lines ]; then
      echo "${DLROBOT_RESULTS} is not updated properly on the first run"
      kill ${WEB_SERVER_PID}
      exit 1
  fi
}

run_worker 1
run_worker 2

#no more retries
run_worker 2


kill ${WEB_SERVER_PID}

