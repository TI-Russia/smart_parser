Cозданиr базы disclosures=dlrobot+declarator

#1. получение двух репозиториев:
    git declarator в ~/declarator и
    git smart_parser в ~/smart_parser

 export DISCLOSURES_FOlDER=~/smart_parser/tools/diclosures
 export SCRIPT_FOLDER=$DISCLOSURES_FOlDER/scripts
 export DLROBOT_FOLDER=~/declarator_hdd/declarator/DATE

#2. создание нового каталога для dlrobot и файлов слияния
    mkdir $DLROBOT_FOLDER


#3. Запуск dlrobot (todo нужно описаять), получение каталога domains
   (здесь все пока запускалось руками, общего скрипта  нет)

#4.  запуск smart_parser
    cd $DLROBOT_FOLDER
    cp ~/smart_parser/tools/CorpusProcess/ubuntu_parallel/*.sh .
    bash run_smart_parser_all.sh

#5.  получить все файлы из declarator в каталог out.documentfile и создать файл human_files.json
    cd $DLROBOT_FOLDER
    ALL_HUMAN_FILES_FOLDER=out.documentfile
    python $SCRIPT_FOLDER/download_all_documents.py --table declarations_documentfile --output-folder $ALL_HUMAN_FILES_FOLDER
    python $SCRIPT_FOLDER/create_json_by_human_files.py --folder $ALL_HUMAN_FILES_FOLDER --table declarations_documentfile --output-json human_files.json

#6.  слияние по файлам dlrobot и declarator, получение dlrobot_human.json
    cd $DLROBOT_FOLDER
    python $SCRIPT_FOLDER/join_human_and_dlrobot.py --dlrobot-folder domains --human-json human_files.json --output-json dlrobot_human.json


#7.  создание базы disclosures
    cd $DISCLOSURES_FOlDER
    cat create_disclosures_db.sql | sudo mysql
    python manage.py makemigrations
    python manage.py migrate
    cd $DLROBOT_FOLDER

#8.  Импорт json в dislosures_db
   cd $DLROBOT_FOLDER
   python $DISCLOSURES_FOlDER/manage.py import_json --smart-parser-human-json-folder human_smart_parser_jsons  --dlrobot-human dlrobot_human.json  --process-count 4
   python $DISCLOSURES_FOlDER/manage.py copy_person_id

#9.  запуск сливалки
   /to do

