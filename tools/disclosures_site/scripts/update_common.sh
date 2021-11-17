#common variables
export TOOLS=$HOME/smart_parser/tools
export ASPOSE_LIC=$HOME/lic.bin
export PYTHONPATH=$TOOLS/disclosures_site:$TOOLS
export DECLARATOR_CONV_URL=c.disclosures.ru:8091


export CENTRAL_HOST_NAME=migalka
export DLROBOT_CENTRAL_FOLDER=~/declarator_hdd/declarator/dlrobot_central
export DLROBOT_UPDATES_FOLDER=~/declarator_hdd/declarator/dlrobot_updates
export YANDEX_DISK_FOLDER=~/declarator_hdd/Yandex.Disk/declarator
export HUMAN_FILES_JSON=$YANDEX_DISK_FOLDER/human_files.dbm
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons
export DEDUPE_MODEL=$TOOLS/disclosures_site/deduplicate/model/random_forest.pickle
export DISCLOSURES_DB_HOST=migalka
export DEDUPE_HOSTS=$'avito\nsamsung'
export SMART_PARSER_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8165
export DLROBOT_CENTRAL_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8089
export SOURCE_DOC_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8090

export FRONTEND=sel-disclosures
export FRONTEND_SRC=/home/sokirko/smart_parser
export FRONTEND_WEB_SITE=/home/sokirko/smart_parser/tools/disclosures_site
export FRONTEND_DLROBOT_MONITORING_FOLDER=$FRONTEND_WEB_SITE/disclosures/static/dlrobot

export ACCESS_LOG_ARCHIVE=$YANDEX_DISK_FOLDER/nginx_logs
export PROD_SOURCE_DOC_SERVER=195.70.213.239
