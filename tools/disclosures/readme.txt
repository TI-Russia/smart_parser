Cозданиr базы disclosures=dlrobot+declarator

#1. получение двух репозиториев:
    git declarator в ~/declarator и
    git smart_parser в ~/smart_parser

export DISCLOSURES_FOlDER=~/smart_parser/tools/diclosures
export SCRIPT_FOLDER=$DISCLOSURES_FOlDER/scripts
CURRENT_DATE=`date  +'%Y-%m-%d'`
export DLROBOT_FOLDER=~/declarator_hdd/declarator/$CURRENT_DATE
export HUMAN_FILES_JSON=human_files.json
export ALL_HUMAN_FILES_FOLDER=~/declarator_hdd/declarator/human_files
export INPUT_DLROBOT_PROJECTS=input_projects
export DLROBOT_RESULT_FOLDER=domains

#2. создание нового каталога dlrobot  (стоит переименовать в disclosures)
    mkdir $DLROBOT_FOLDER
    cd $DLROBOT_FOLDER

№3  получить все новые (!) файлы из declarator в каталог $ALL_HUMAN_FILES_FOLDER и создать файл human_files.json
    python $SCRIPT_FOLDER/export_human_files.py --table declarations_documentfile --output-folder $ALL_HUMAN_FILES_FOLDER --output-json $HUMAN_FILES_JSON


#4. Запуск dlrobot, получение каталога domains
    python ~/smart_parser/tools/robots/dlrobot/scripts/check_domains.py --human-files $HUMAN_FILES_JSON --reached-domains domains.txt  --timeouted-domains timeouted-domains.txt
    python ~/smart_parser/tools/robots/dlrobot/scripts/create_by_domains.py --domains domains.txt --output-folder $INPUT_DLROBOT_PROJECTS
    # деление на 7 порций пока было сделано руками
    ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run.sh $INPUT_DLROBOT_PROJECTS $DLROBOT_FOLDER/processed_projects
    python ~/smart_parser/tools/disclosures/scripts/copy_dlrobot_documents_to_one_folder.py --input-glob  processed_projects.* --output-folder $DLROBOT_RESULT_FOLDER


#5.  слияние по файлам dlrobot и declarator, получение dlrobot_human.json
    python $SCRIPT_FOLDER/join_human_and_dlrobot.py --dlrobot-folder domains --human-json $HUMAN_FILES_JSON --output-json dlrobot_human.json

#6.  запуск smart_parser
    bash ~/smart_parser/tools/CorpusProcess/ubuntu_parallel/run_smart_parser_all.sh $DLROBOT_RESULT_FOLDER migalka,oldtimer,ventil,lena


#7.  создание базы disclosures
    cd $DISCLOSURES_FOlDER
    cat create_disclosures_db.sql | sudo mysql
    python manage.py makemigrations
    python manage.py migrate
    cd $DLROBOT_FOLDER

#8.  Импорт json в dislosures_db
   python $DISCLOSURES_FOlDER/manage.py import_json --smart-parser-human-json-folder human_smart_parser_jsons  --dlrobot-human dlrobot_human.json  --process-count 4
   python $DISCLOSURES_FOlDER/manage.py copy_person_id

#9.  запуск сливалки, 3 gb each char
   cd $DISCLOSURES_FOlDER
   export DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.infoexport DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.info
   cat data/abc.txt | xargs -P 2 -t -n 1 -I {}  python manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --result-pairs-file dedupe_result.{}.txt  --family-prefix {} --write-to-db

