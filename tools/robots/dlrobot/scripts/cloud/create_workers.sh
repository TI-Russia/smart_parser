HOME_DIR=/home/sokirko
export ASPOSE_LIC=$HOME_DIR/lic.bin
export PYTHONPATH=$HOME_DIR/smart_parser/tools
export DECLARATOR_CONV_URL=disclosures.ru:8091
export DLROBOT_CENTRAL_URL=disclosures.ru:8089


function create_worker() {
  local path=$1
  if [ -d $path ]; then
    rm -rf $path
  fi

  mkdir -p $path
  cd $path
  nohup /usr/bin/python3 $HOME_DIR/smart_parser/tools/robots/dlrobot/scripts/cloud/dlrobot_worker.py \
              --server-address $DLROBOT_CENTRAL_URL  --tmp-folder /tmp --run-forever &
}

workers_count=`ps -x | grep -c dlrobot_worker.py`
if [ $workers_count != 1 ]; then
  echo "process workers are still running, delete workers first"
  exit 1
fi

create_worker /tmp/dlrobot_worker1
create_worker /tmp/dlrobot_worker2