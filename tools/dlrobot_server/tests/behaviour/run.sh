PROJECT=$1
export DLROBOT_CENTRAL_SERVER_ADDRESS=$2
WORKDIR=workdir
cd "$(dirname "$0")"
RESULT_FOLDER=processed_projects
export INPUT_CENTRAl_FOLDER=input_projects

rm -rf $RESULT_FOLDER *.log $WORKDIR .dlrobot_pit_stop

mkdir $INPUT_CENTRAl_FOLDER
cp $PROJECT $INPUT_CENTRAl_FOLDER

python3 ../../dlrobot_worker.py start --working-folder $WORKDIR --timeout-before-next-task 2&
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

python3 ../../dlrobot_central.py --result-folder  ${RESULT_FOLDER} --disable-smart-parser-cache --central-heart-rate 1s &
CENTRAL_PID=$!
sleep 1
touch ".dlrobot_pit_stop"
sleep 3
kill -0 $CENTRAL_PID
if [ $?  == 0 ]; then
    echo "worker must exit after creating .dlrobot_pit_stop"
    kill $CENTRAL_PID
    exit 1
fi


echo "ok"
exit 0
