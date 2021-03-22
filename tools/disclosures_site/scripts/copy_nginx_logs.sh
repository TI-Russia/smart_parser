COMMON_SCRIPT=$(dirname $0)/update_common.sh
source $COMMON_SCRIPT

LOG_ARCHIVE=$YANDEX_DISK_FOLDER/nginx_logs
FRONTEND_NGINX_LOGS=/var/log/nginx
FRONTEND_OUTPUT_FOLDER=$TOOLS/disclosures/static/dlrobot
DATE=`date "+\%Y-\%m-\%d"`

ssh $FRONTEND sudo chmod a+r $FRONTEND_NGINX_LOGS/access.log
scp $FRONTEND:$FRONTEND_NGINX_LOGS/access.log $LOG_ARCHIVE/access.$DATE
gzip --force $LOG_ARCHIVE/access.$DATE

ssh $FRONTEND sudo chmod a+r $FRONTEND_NGINX_LOGS/error.log
scp $FRONTEND:$FRONTEND_NGINX_LOGS/error.log $LOG_ARCHIVE/error.$DATE
gzip --force $LOG_ARCHIVE/error.$DATE

