COMMON_SCRIPT=$(dirname $0)/../update_common.sh
source $COMMON_SCRIPT

export CENTRAL_STATS=$DLROBOT_CENTRAL_FOLDER/processed_projects/dlrobot_remote_calls.dat
export CONV_STATS=/home/sokirko/declarator_hdd/declarator/convert_stats.txt

python3 $TOOLS/ConvStorage/scripts/get_stats.py --history-file $CONV_STATS

python3 $TOOLS/disclosures_site/scripts/monitoring/dl_monitoring.py --central-stats-file  $CENTRAL_STATS \
    --conversion-server-stats $CONV_STATS --central-server-cpu-and-mem  /tmp/glances.dat --output-folder /tmp/dlrobot

scp /tmp/dlrobot/* $FRONTEND:$FRONTEND_OUTPUT_FOLDER

