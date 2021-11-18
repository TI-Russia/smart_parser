COMMON_SCRIPT=$(dirname $0)/profile.sh
source $COMMON_SCRIPT # import ACCESS_LOG_ARCHIVE

FRONTEND_NGINX_LOGS=/var/log/nginx
FRONTEND_OUTPUT_FOLDER=$TOOLS/disclosures/static/dlrobot
DATE=`date "+%Y-%m-%d"`

function copy_log() {
  local log_name=$1
  local local_log_path=$ACCESS_LOG_ARCHIVE/$log_name.$DATE
  ssh $FRONTEND sudo chmod a+r $FRONTEND_NGINX_LOGS/$log_name.log
  scp $FRONTEND:$FRONTEND_NGINX_LOGS/$log_name.log $local_log_path
  if [ ! -s $local_log_path ]; then
    echo "$local_log_path is empty";
    /home/sokirko/.local/bin/telegram-send "$local_log_path is empty, no page visitors?"
    exit 1
  fi
  gzip --force $local_log_path
}

copy_log access
copy_log error

