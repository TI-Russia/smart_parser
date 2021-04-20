COMMON_SCRIPT=$(dirname $0)/../update_common.sh
source $COMMON_SCRIPT
export TMP_FOLDER=/tmp/dlrobot_monitoring
export CENTRAL_STATS=$TOOLS/web_site_db/data/dlrobot_remote_calls.dat
export CONV_STATS=/home/sokirko/declarator_hdd/declarator/convert_stats.txt


python3 $TOOLS/ConvStorage/scripts/get_stats.py --history-file $CONV_STATS

rm -rf $TMP_FOLDER;
mkdir $TMP_FOLDER;

python3 $TOOLS/disclosures_site/scripts/monitoring/dl_monitoring.py --central-stats-file  $CENTRAL_STATS \
    --conversion-server-stats $CONV_STATS --central-server-cpu-and-mem  /tmp/glances.dat --output-folder $TMP_FOLDER

scp $TMP_FOLDER/* $FRONTEND:$FRONTEND_DLROBOT_MONITORING_FOLDER

