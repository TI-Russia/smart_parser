DUMMY=$1
WEB_ADDR=$2
WORKDIR=workdir
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects

rm -rf $RESULT_FOLDER *.log $WORKDIR

python3 ../../scripts/cloud/dlrobot_worker.py start --server-address ${WEB_ADDR} --working-folder $WORKDIR --timeout-before-next-task 2 &
WORKER_PID=$!
sleep 3
kill -0 $WORKER_PID
if [ $?  != 0 ]; then
    echo "worker must be active even when central is down "
    kill ${WORKER_PID}
    exit 1
fi

touch $WORKDIR/".dlrobot_pit_stop"
sleep 3
kill -0 $WORKER_PID
if [ $?  == 0 ]; then
    echo "worker must quit, since I have created file .dlrobot_pit_stop  "
    kill ${WORKER_PID}
    exit 1
fi

echo "ok"
exit 0
