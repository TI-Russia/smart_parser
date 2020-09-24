DUMMY=$1
WEB_ADDR=$2
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects
WORKER_DIR=${TMPDIR:-/tmp}
rm -rf $RESULT_FOLDER

python ../../scripts/cloud/dlrobot_central.py --server-address ${WEB_ADDR} --input-folder input_projects --result-folder  ${RESULT_FOLDER} &
WEB_SERVER_PID=$!
sleep 1

python ../../scripts/cloud/dlrobot_worker.py --server-address ${WEB_ADDR} --tmp-folder ${WORKER_DIR}

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_results.dat
number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}'`
if [ ${number_projects} != 1 ]; then
    echo "${DLROBOT_RESULTS} is not updated properly on the first run"
    kill ${WEB_SERVER_PID}
    exit 1
fi

if [ ! -f ${RESULT_FOLDER}/aot.ru/aot.ru.txt.clicks ]; then
  echo "aot.ru.txt.clicks is not sent by the worker"
  kill ${WEB_SERVER_PID}
  exit 1
fi

#one more worker run, but there are no jobs
python ../../scripts/cloud/dlrobot_worker.py --server-address ${WEB_ADDR} --tmp-folder ${WORKER_DIR}
number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}' `
if [ ${number_projects} != 1 ]; then
    echo "${DLROBOT_RESULTS} is not updated properly on the second run"
    kill ${WEB_SERVER_PID}
    exit 1
fi

kill ${WEB_SERVER_PID}

