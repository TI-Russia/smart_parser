#1.2. Объявление переменных (кроме тех, что уже объявлены в ~/smart_parser/tools/INSTALL.txt)

# todo: выписывать smart_parser в $DLROBOT_FOLDER и делать ссылку на него в проде
export TOOLS=/home/sokirko/smart_parser/tools
export DLROBOT_CENTRAL_FOLDER=~/declarator_hdd/declarator/dlrobot_central
export DLROBOT_UPDATES_FOLDER=~/declarator_hdd/declarator/dlrobot_updates
export YANDEX_DISK_FOLDER=~/declarator_hdd/Yandex.Disk/declarator
export HUMAN_FILES_JSON=$YANDEX_DISK_FOLDER/human_files.json
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons
export PYTHONPATH=$TOOLS/disclosures_site:$TOOLS

export DEDUPE_MODEL=$TOOLS/disclosures_site/deduplicate/model/random_forest.pickle
export DISCLOSURES_DB_HOST=migalka
export DEDUPE_HOSTS=lena,avito,samsung

export CENTRAL_HOST_NAME=migalka
export SMART_PARSER_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8165
export DLROBOT_CENTRAL_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8089
export SOURCE_DOC_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8090
export DECLARATOR_CONV_URL=c.disclosures.ru:8091

export FRONTEND=sel-disclosures
export FRONTEND_DLROBOT_MONITORING_FOLDER=/home/sokirko/smart_parser/tools/disclosures_site/disclosures/static/dlrobot

export ACCESS_LOG_ARCHIVE=$YANDEX_DISK_FOLDER/nginx_logs
export PROD_SOURCE_DOC_SERVER=195.70.213.239
export ASPOSE_LIC=/home/sokirko/lic.bin