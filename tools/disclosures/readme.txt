#Cоздание базы disclosures=dlrobot+declarator

#1.1 получение declarator:
    cd ~
    git clone sokirko@bitbucket.org:TI-Russia/declarator.git
    cd declarator/trasparency
    pip3 install -r ../deploy/requirements.txt
    echo "CREATE DATABASE declarator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    create user if not exists 'declarator'@ identified by 'declarator';
    GRANT ALL PRIVILEGES ON *.* TO 'declarator'@;" | mysql
    wget https://declarator.org/manage/dump_files/prod????.tar.gz
    zcat prod????.tar.gz | mysql -D declarator

#1.2
    git clone git@github.com:TI-Russia/smart_parser.git ~/smart_parser

export DISCLOSURES_FOlDER=~/smart_parser/tools/disclosures
CURRENT_DATE=`date  +'%Y-%m-%d'`
export DLROBOT_FOLDER=~/declarator_hdd/declarator/$CURRENT_DATE
export HUMAN_FILES_JSON=human_files.json
export HUMAN_FILES_FOLDER=~/declarator_hdd/declarator/human_files
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons

export INPUT_DLROBOT_PROJECTS=input_projects
export DLROBOT_RESULT_FOLDER=domains

#2. создание нового каталога dlrobot  (стоит переименовать в disclosures)
    mkdir $DLROBOT_FOLDER
    cd $DLROBOT_FOLDER

№3  получить все новые (!) файлы из declarator в каталог $HUMAN_FILES_FOLDER и создать файл human_files.json
    python $DISCLOSURES_FOlDER/scripts/export_human_files.py --table declarations_documentfile --output-folder $HUMAN_FILES_FOLDER --output-json $HUMAN_FILES_JSON


#4. Запуск dlrobot, получение каталога domains
    python ~/smart_parser/tools/robots/dlrobot/scripts/check_domains.py --human-files $HUMAN_FILES_JSON --reached-domains domains.txt  --timeouted-domains timeouted-domains.txt
    python ~/smart_parser/tools/robots/dlrobot/scripts/create_by_domains.py --domains domains.txt --output-folder $INPUT_DLROBOT_PROJECTS
    # деление на 7 порций пока было сделано руками (надо вспомнить, что-то такое ls|shuf|split -l 1000 ... или написать скрипт на питоне
    ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run.sh $INPUT_DLROBOT_PROJECTS.01 $DLROBOT_FOLDER/processed_projects.01
    ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run.sh $INPUT_DLROBOT_PROJECTS.03 $DLROBOT_FOLDER/processed_projects.02
    ...
    ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run.sh $INPUT_DLROBOT_PROJECTS.03 $DLROBOT_FOLDER/processed_projects.07
    python3 ~/smart_parser/tools/disclosures/scripts/copy_dlrobot_documents_to_one_folder.py --input-glob  processed_projects.* --output-folder $DLROBOT_RESULT_FOLDER


#5.  слияние по файлам dlrobot и declarator, получение dlrobot_human.json
    python $DISCLOSURES_FOlDER/scripts/join_human_and_dlrobot.py --dlrobot-folder domains --human-json $HUMAN_FILES_JSON --output-json dlrobot_human.json

#6.  запуск smart_parser
    bash ~/smart_parser/tools/CorpusProcess/ubuntu_parallel/run_smart_parser_all.sh $DLROBOT_RESULT_FOLDER migalka,oldtimer,ventil,lena

#6.1 создание ручных json
    [ -d  $HUMAN_JSONS_FOLDER ] || mkdir $HUMAN_JSONS_FOLDER
    cd ~/declarator/transparency
    source ../venv/bin/activate
    python3 manage.py export_in_smart_parser_format --output-folder $HUMAN_JSONS_FOLDER

#7.  инициализация базы disclosures
    follow $DISCLOSURES_FOlDER/INSTALL.txt


#8.  Импорт json в dislosures_db
   cd $DLROBOT_FOLDER
   cat $DISCLOSURES_FOlDER/clear_database.sql | mysql -D disclosures_db -u disclosures -pdisclosures
   python $DISCLOSURES_FOlDER/manage.py import_json --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER  --dlrobot-human dlrobot_human.json  --process-count 4
   python $DISCLOSURES_FOlDER/manage.py copy_person_id

#9.  запуск сливалки, 3 gb each char
   cd $DISCLOSURES_FOlDER
   export DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.infoexport DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.info
   cat data/abc.txt | xargs -P 2 -t -n 1 -I {}  python manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --result-pairs-file dedupe_result.{}.txt  --family-prefix {} --write-to-db


№10 удаление ненужных файлов
    cd $DLROBOT_FOLDER
    rm -rf $DLROBOT_RESULT_FOLDER
