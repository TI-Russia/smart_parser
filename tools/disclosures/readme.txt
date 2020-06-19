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
export OLD_DLROBOT_FOLDER=~/declarator_hdd/2020-02-01
export DLROBOT_FOLDER=~/declarator_hdd/declarator/$CURRENT_DATE
export HUMAN_FILES_JSON=human_files.json
export HUMAN_FILES_FOLDER=~/declarator_hdd/declarator/human_files
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons

export INPUT_DLROBOT_PROJECTS=input_projects
export DLROBOT_RESULT_FOLDER=domains

#2. создание нового каталога dlrobot  (стоит переименовать в disclosures)
    mkdir $DLROBOT_FOLDER
    cd $DLROBOT_FOLDER

#3  получить все новые (!) файлы из declarator в каталог $HUMAN_FILES_FOLDER и создать файл human_files.json
    python $DISCLOSURES_FOLDER/scripts/export_human_files.py --table declarations_documentfile --output-folder $HUMAN_FILES_FOLDER --output-json $HUMAN_FILES_JSON

#3.1  Отправляем все новые Pdf на конвертацию
    find $HUMAN_FILES_FOLDER -name '*.pdf' |  xargs --verbose -n 10  python ~/smart_parser/tools/ConvStorage/scripts/convert_pdf.py --skip-receiving

#4. Запуск dlrobot, получение каталога domains
    # optional python ~/smart_parser/tools/robots/dlrobot/scripts/check_domains.py --human-files $HUMAN_FILES_JSON --reached-domains ../domains/new_domains.txt  --timeouted-domains timeouted-domains.txt
    python ~/smart_parser/tools/robots/dlrobot/scripts/create_by_domains.py --domains ~/smart_parser/tools/robots/dlrobot/domains.txt --domains ~/smart_parser/tools/robots/dlrobot/domains/fix_region.txt --output-folder $INPUT_DLROBOT_PROJECTS --portion-size 1000
    for d in INPUT_DLROBOT_PROJECTS*; do
        portion_id="${filename##*.}"
        ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run.sh $d $DLROBOT_FOLDER/processed_projects.$portion_id
    done
    python ~/smart_parser/tools/disclosures/scripts/copy_dlrobot_documents_to_one_folder.py --input-glob  'processed_projects.*' --output-folder $DLROBOT_RESULT_FOLDER


#5.  слияние по файлам dlrobot, declarator  и старого disclosures , получение dlrobot_human.json
    python $DISCLOSURES_FOLDER/scripts/join_human_and_dlrobot.py --dlrobot-folder $DLROBOT_RESULT_FOLDER \
        --human-json $HUMAN_FILES_JSON --old-dlrobot-human-json $OLD_DLROBOT_FOLDER/dlrobot_human.json \
        --output-json dlrobot_human.json

#5.1  получение статистики по dlrobot_human.json, сравнение с предыдущим обходом
    python $DISCLOSURES_FOLDER/scripts/join_human_and_dlrobot.py dlrobot_human.json > dlrobot_human.json.stats

#6.  запуск smart_parser
    bash ~/smart_parser/tools/CorpusProcess/ubuntu_parallel/run_smart_parser_all.sh $DLROBOT_RESULT_FOLDER migalka,oldtimer,ventil,lena

#6.1 создание ручных json
    [ -d  $HUMAN_JSONS_FOLDER ] || mkdir $HUMAN_JSONS_FOLDER
    cd ~/declarator/transparency
    source ../venv/bin/activate
    python3 manage.py export_in_smart_parser_format --output-folder $HUMAN_JSONS_FOLDER

#7.  инициализация базы disclosures
    follow $DISCLOSURES_FOLDER/INSTALL.txt


#8.  Импорт json в dislosures_db
   cd $DLROBOT_FOLDER
   cat $DISCLOSURES_FOlDER/clear_database.sql | mysql -D disclosures_db -u disclosures -pdisclosures
   python $DISCLOSURES_FOLDER/manage.py import_json --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER  --dlrobot-human dlrobot_human.json  --process-count 4 --settings disclosures.settings.dev
   python $DISCLOSURES_FOLDER/manage.py copy_person_id --settings disclosures.settings.dev

#9.  запуск сливалки, 3 gb each char
   cd $DISCLOSURES_FOLDER
   export DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.infoexport DEDUPE_MODEL=~/declarator/transparency/model.baseline/dedupe.info
   cat data/abc.txt | xargs -P 2 -t -n 1 -I {}  python manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --result-pairs-file dedupe_result.{}.txt  --family-prefix {} --write-to-db


№10 удаление ненужных файлов
    cd $DLROBOT_FOLDER
    rm -rf $DLROBOT_RESULT_FOLDER
