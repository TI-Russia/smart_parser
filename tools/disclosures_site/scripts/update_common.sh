#1.2. Объявление переменных (кроме тех, что уже объявлены в ~/smart_parser/tools/INSTALL.txt)

# todo: выписывать smart_parser в $DLROBOT_FOLDER и делать ссылку на него в проде
export TOOLS=/home/sokirko/smart_parser/tools
export DLROBOT_CENTRAL_FOLDER=~/declarator_hdd/declarator/dlrobot_central
export DLROBOT_UPDATES_FOLDER=~/declarator_hdd/declarator/dlrobot_updates
export HUMAN_FILES_JSON=~/declarator_hdd/Yandex.Disk/declarator/human_files.json
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons
export YANDEX_DISK_FOLDER=~/declarator_hdd/Yandex.Disk/declarator
export PYTHONPATH=$TOOLS/disclosures_site:$TOOLS

export DEDUPE_MODEL=$TOOLS/disclosures_site/deduplicate/model/random_forest.pickle
export DISCLOSURES_DB_HOST=migalka
export DEDUPE_HOSTS=lena,avito
export DEDUPE_HOSTS_SPACES="lena avito"

export CENTRAL_HOST_NAME=migalka
export SMART_PARSER_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8165
export DLROBOT_CENTRAL_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8089
export SOURCE_DOC_SERVER_ADDRESS=$CENTRAL_HOST_NAME:8090
export DECLARATOR_CONV_URL=c.disclosures.ru:8091
export FRONTEND=sel-disclosures
export ACCESS_LOG_ARCHIVE=$YANDEX_DISK_FOLDER/nginx_logs
