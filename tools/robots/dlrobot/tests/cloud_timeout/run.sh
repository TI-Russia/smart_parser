DUMMY=$1
export DLROBOT_CENTRAL_SERVER_ADDRESS=$2
RESULT_FOLDER=processed_projects

rm -rf $RESULT_FOLDER *.log

python3 ../../scripts/cloud/dlrobot_central.py \
    --tries-count 1 --input-folder input_projects --result-folder  ${RESULT_FOLDER}  --central-heart-rate  1s --dlrobot-project-timeout 2s --disable-smart-parser-cache &
WEB_SERVER_PID=$!
sleep 2


python3 ../../scripts/cloud/dlrobot_worker.py run_once --working-folder workdir &
WORKER_PID=$!
sleep 2
kill ${WORKER_PID}
sleep 2

DLROBOT_RESULTS=${RESULT_FOLDER}/dlrobot_remote_calls.dat
number_projects=`wc ${DLROBOT_RESULTS} -l | awk '{print $1}'`
if [ ! -f ${DLROBOT_RESULTS} ] || [ ${number_projects} != 1 ]; then
    echo "${DLROBOT_RESULTS} must contain a timeouted remote call "
    kill ${WEB_SERVER_PID}
    exit 1
fi

input_tasks_count=`curl http://$DLROBOT_CENTRAL_SERVER_ADDRESS/stats | jq '.input_tasks'`

if [ $input_tasks_count != "1" ]; then
    echo "input task queue must must contain the input project though --tries-count is set to 1, because of timeout (or workstation down)"
    kill ${WEB_SERVER_PID}
    exit 1
fi

kill ${WEB_SERVER_PID}

