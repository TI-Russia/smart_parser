# Процесс создание базы disclosures = dlrobot+declarator

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

#1.2 получение smart_parser:
    git clone git@github.com:TI-Russia/smart_parser.git ~/smart_parser

#1.3 Объявление переменных

export TOOLS=~/smart_parser/tools
CURRENT_DATE=`date  +'%Y-%m-%d'`
export OLD_DLROBOT_FOLDER=~/declarator_hdd/declarator/2020-02-01
export DLROBOT_FOLDER=~/declarator_hdd/declarator/$CURRENT_DATE
export HUMAN_FILES_JSON=human_files.json
export HUMAN_FILES_FOLDER=~/declarator_hdd/declarator/human_files
export HUMAN_JSONS_FOLDER=~/declarator_hdd/declarator/human_jsons

export INPUT_DLROBOT_PROJECTS=input_projects
export DISCLOSURES_FILES=domains
export PYTHONPATH=$TOOLS/disclosures:$TOOLS
export HOSTS=migalka,oldtimer,ventil,lena

#2. создание нового каталога dlrobot  (стоит переименовать в disclosures)
    mkdir $DLROBOT_FOLDER
    cd $DLROBOT_FOLDER

#3  получить все новые (!) файлы из declarator в каталог $HUMAN_FILES_FOLDER и создать файл human_files.json
    python $TOOLS/disclosures/scripts/export_human_files.py --table declarations_documentfile --output-folder $HUMAN_FILES_FOLDER --output-json $HUMAN_FILES_JSON

#3.1  Отправляем все новые Pdf на конвертацию
    find $HUMAN_FILES_FOLDER -name '*.pdf' |  xargs --verbose -n 10  python $TOOLS/ConvStorage/scripts/convert_pdf.py --skip-receiving

#4. Запуск dlrobot, получение каталога domains
    # optional python $TOOLS/robots/dlrobot/scripts/check_domains.py --human-files $HUMAN_FILES_JSON --reached-domains ../domains/new_domains.txt  --timeouted-domains timeouted-domains.txt
    python $TOOLS/robots/dlrobot/scripts/create_by_domains.py --domains $TOOLS/robots/dlrobot/domains.txt --domains $TOOLS/robots/dlrobot/domains/fix_region.txt --output-folder $INPUT_DLROBOT_PROJECTS --portion-size 1000
    for d in INPUT_DLROBOT_PROJECTS*; do
        portion_id="${filename##*.}"
        $TOOLS/robots/dlrobot/scripts/ubuntu_parallel/run.sh $d $DLROBOT_FOLDER/processed_projects.$portion_id $HOSTS
    done
    python $TOOLS/disclosures/scripts/copy_dlrobot_documents_to_one_folder.py --input-glob  'processed_projects.*' --output-folder $DISCLOSURES_FILES --output-json copy_to_one_folder.json


#5.  слияние по файлам dlrobot, declarator  и старого disclosures , получение dlrobot_human.json
    python $TOOLS/disclosures/scripts/join_human_and_dlrobot.py --dlrobot-folder $DISCLOSURES_FILES  --copy-to-one-folder-json copy_to_one_folder.json \
        --human-json $HUMAN_FILES_JSON --old-dlrobot-human-json $OLD_DLROBOT_FOLDER/dlrobot_human.json \
        --output-json dlrobot_human.json


#5.1  получение статистики по dlrobot_human.json, сравнение с предыдущим обходом
    python $TOOLS/disclosures/scripts/dlrobot_human_stats.py dlrobot_human.json > dlrobot_human.json.stats

#5.2  факультативно, переконвертация  pdf, которые не были переконвертированы раньше
 find  $DISCLOSURES_FILES -name '*.pdf' -type f | xargs -n 100 --verbose python $TOOLS/ConvStorage/scripts/convert_pdf.py --skip-receiving --conversion-timeout 20

#5.3  Запуск текущего классификатора на старых файлах из dlrobot и удаление тех, что не прошел классификатор
  find  $DISCLOSURES_FILES -name 'o*' -type f | xargs -P 4 -n 1 --verbose python $TOOLS/DeclDocRecognizer/dlrecognizer.py --delete-negative --source-file
  python $TOOLS/disclosures/scripts/clear_json_entries_for_deleted_files.py dlrobot_human.json
  python $TOOLS/disclosures/scripts/dlrobot_human_stats.py dlrobot_human.json > dlrobot_human.json.stats  

#6.  запуск smart_parser
    bash $TOOLS/CorpusProcess/ubuntu_parallel/run_smart_parser_all.sh $DLROBOT_FOLDER/$DISCLOSURES_FILES $HOSTS

#6.1 создание ручных json
    [ -d  $HUMAN_JSONS_FOLDER ] || mkdir $HUMAN_JSONS_FOLDER
    cd ~/declarator/transparency
    source ../venv/bin/activate
    python3 manage.py export_in_smart_parser_format --output-folder $HUMAN_JSONS_FOLDER

#7.  инициализация базы disclosures
    follow $TOOLS/disclosures/INSTALL.txt


#8.  Импорт json в dislosures_db
   cd $DLROBOT_FOLDER
   cat $TOOLS/disclosures/clear_database.sql | mysql -D disclosures_db -u disclosures -pdisclosures
   python $TOOLS/disclosures/manage.py import_json --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER  --dlrobot-human dlrobot_human.json  --process-count 4 --settings disclosures.settings.prod
   python $TOOLS/disclosures/manage.py copy_person_id --settings disclosures.settings.prod

#9.  тестирование сливалки
   export DEDUPE_MODEL=~/declarator/transparency/toloka/dedupe_model/dedupe.info

   cd $TOOLS/disclosures/toloka/pools
   bash -x make_pools.sh

#10.  запуск сливалки, 4 gb memory each family portion, 30 GB temp files, no more than one process per workstation
   cd $TOOLS/disclosures
   export SURNAME_SPANS=`python manage.py generate_dedupe_pairs  --print-family-prefixes   --settings disclosures.settings.prod`
   export DISCLOSURES_DB_HOST=migalka
   echo $HOSTS  |  tr "," "\n" | xargs --verbose -n 1 -I {} ssh {} git  -C ~/smart_parser pull
   cat clear_dedupe_artefacts.sql | mysql -D disclosures_db -u disclosures -pdisclosures

   parallel --jobs 1 -a - --env DISCLOSURES_DB_HOST --env PYTHONPATH -S $HOSTS --basefile $DEDUPE_MODEL  --verbose \
   python $TOOLS/disclosures/manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --surname-bounds {} --write-to-db --settings disclosures.settings.prod ::: $SURNAME_SPANS



№11 удаление ненужных файлов (факультативно)
    cd $DLROBOT_FOLDER
    rm -rf $DISCLOSURES_FILES

#12 перенос на прод
   mysqldump -u disclosures -pdisclosures disclosures_db  |  gzip -c > $DLROBOT_FOLDER/disclosures.sql.gz

   #go to prod (oldtimer)
   cat $TOOLS/disclosures/clear_database.sql | mysql -D disclosures_db -u disclosures -pdisclosures
   zcat $DLROBOT_FOLDER/disclosures.sql.gz | mysql -D disclosures_db -u disclosures -pdisclosures
   python3  manage.py search_index --rebuild -f    --settings disclosures.settings.prod -v3
