function create_worker() {
  local path=$1
  if [ ! -d $path ]; then
    mkdir -p $path
    cd $path
    rm nohup.out; nohup python3 ~/smart_parser/tools/robots/dlrobot/scripts/cloud/dlrobot_worker.py \
              --server-address disclosures.ru:8089  --tmp-folder /tmp --run-forever &
    cd -
  fi
}

workers_count=`ps -x | grep -c dlrobot_worker`
if [ $workers_count != 1 ]; then
  echo "process workers are still running, delete workers first"
  exit 1
fi

create_worker /tmp/dlrobot_worker1
create_worker /tmp/dlrobot_worker2