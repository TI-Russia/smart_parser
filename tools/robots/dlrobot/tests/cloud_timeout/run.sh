DUMMY=$1
WEB_ADDR=$2
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects

rm -rf $RESULT_FOLDER *.log

python3 ../../scripts/cloud/dlrobot_central.py --server-address ${WEB_ADDR} \
    --input-folder input_projects --result-folder  ${RESULT_FOLDER}  --central-heart-rate  1s --dlrobot-project-timeout 2s&
WEB_SERVER_PID=$!
sleep 2


python3 ../../scripts/cloud/dlrobot_worker.py run_once --server-address ${WEB_ADDR} --working-folder workdir &
WORKER_PID=$!
sleep 2
kill ${WORKER_PID}
sleep 2

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_remote_calls.dat
number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}'`
if [ ! -f ${DLROBOT_RESULTS} ] || [ ${number_projects} != 1 ]; then
    echo "${DLROBOT_RESULTS} must contain a timouted remote call "
    kill ${WEB_SERVER_PID}
    exit 1
fi

kill ${WEB_SERVER_PID}

