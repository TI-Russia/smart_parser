
# Процесс создание базы disclosures = dlrobot+declarator (раз в месяц?)

#0 ~/smart_parser/tools/INSTALL.txt are prerequisites

set -e

source $(dirname $0)/update_common.sh


#1 создание нового каталога и файла настройки .profile
    cd $DLROBOT_UPDATES_FOLDER/
    export OLD_DLROBOT_FOLDER=`find -mindepth 1 -maxdepth 1 -xtype d  | sort | tail -n 1 | xargs -n 1 realpath`
    # all projects that older than 5 hours in order not to get a race condition
    export CRAWL_EPOCH=`python3 -c "import time; print (int(time.time() - 60 * 5))"`
    export DLROBOT_FOLDER=$DLROBOT_UPDATES_FOLDER/$CRAWL_EPOCH

    mkdir -p $DLROBOT_FOLDER
    cd $DLROBOT_FOLDER
    cp $TOOLS/disclosures_site/scripts/update_common.sh  .profile
    echo "" >> .profile
    echo "export DLROBOT_FOLDER=$DLROBOT_FOLDER" >> .profile
    echo "export CRAWL_EPOCH=$CRAWL_EPOCH" >> .profile
    echo "export OLD_DLROBOT_FOLDER=$OLD_DLROBOT_FOLDER" >> .profile

    cp $DLROBOT_CENTRAL_FOLDER/dlrobot_central.log $YANDEX_DISK_FOLDER

#2  слияние по файлам dlrobot, declarator  и старого disclosures, получение dlrobot_human.json
    python3 $TOOLS/disclosures_site/scripts/join_human_and_dlrobot.py \
        --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder  "$DLROBOT_CENTRAL_FOLDER/processed_projects" \
        --human-json $HUMAN_FILES_JSON \
        --old-dlrobot-human-json $OLD_DLROBOT_FOLDER/dlrobot_human.json \
        --output-domains-folder $DISCLOSURES_FILES \
        --output-json dlrobot_human.json


#3  получение статистики по dlrobot_human.json, сравнение с предыдущим обходом
    python3 $TOOLS/disclosures_site/scripts/dlrobot_human_stats.py dlrobot_human.json > dlrobot_human.json.stats
    new_size=$(stat -c%s "dlrobot_human.json")
    old_size=$(stat -c%s "$OLD_DLROBOT_FOLDER/dlrobot_human.json")
    if (( $old_size > $new_size )); then
        echo "the size of dlrobot_human.json is less than the size of older one, check dlrobot_human.json.stats"
        exit 1
    endif

#4 (факультативно) новый смартпарсер через старые файлы dlrobot
  #python3 $TOOLS/robots/dlrobot/scripts/cloud/smart_parser_cache_client.py  --walk-folder-recursive $DISCLOSURES_FILES --action put

#3.5  (факультативно) переконвертация  pdf, которые не были переконвертированы раньше
 #find  $DISCLOSURES_FILES -name '*.pdf' -type f | xargs -n 100 --verbose python $TOOLS/ConvStorage/scripts/convert_pdf.py --skip-receiving --conversion-timeout 20

#3.6  (факультативно) Запуск текущего классификатора на старых файлах из dlrobot и удаление тех, что не прошел классификатор
  #find  $DISCLOSURES_FILES -name 'o*' -type f | xargs -P 4 -n 1 --verbose python $TOOLS/DeclDocRecognizer/dlrecognizer.py --delete-negative --source-file
  #python $TOOLS/disclosures_site/scripts/clear_json_entries_for_deleted_files.py dlrobot_human.json
  #python $TOOLS/disclosures_site/scripts/dlrobot_human_stats.py dlrobot_human.json > dlrobot_human.json.stats


#7  Создание базы первичных ключей старой базы, чтобы поддерживать постоянство веб-ссылок по базе прод
   python3 /var/www/smart_parser/tools/disclosures_site/manage.py create_permalink_storage --settings disclosures.settings.prod --output-dbm-file permalinks.dbm


#8.  инициализация базы disclosures
    cd ~/smart_parser/tools/disclosures_site
    python3 manage.py create_database --settings disclosures.settings.dev --skip-checks
    python3 manage.py makemigrations --settings disclosures.settings.dev
    python3 manage.py migrate --settings disclosures.settings.dev
    python3 manage.py search_index --rebuild  --settings disclosures.settings.dev -f
    python3 manage.py test declarations/tests --settings disclosures.settings.dev

#9
    cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev --permanent-links-db permalinks.dbm


#10  Импорт json в dislosures_db (может быть, стоит запускать в 2 потока, а то памяти на мигалке не хватает)
   python3 $TOOLS/disclosures_site/manage.py clear_database --settings disclosures.settings.dev
   python3 $TOOLS/disclosures_site/manage.py import_json \
               --settings disclosures.settings.dev \
               --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
               --dlrobot-human dlrobot_human.json   \
               --process-count 2  \
               --permanent-links-db permalinks.dbm

   python3 $TOOLS/disclosures_site/manage.py copy_person_id \
        --settings disclosures.settings.dev \
        --permanent-links-db permalinks.dbm

#11.  запуск сливалки, 4 gb memory each family portion, 30 GB temp files, no more than one process per workstation
   python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs  --print-family-prefixes   --permanent-links-db $DLROBOT_FOLDER/permalinks.dbm --settings disclosures.settings.dev > surname_spans.txt
   python3 $TOOLS/disclosures_site/manage.py clear_dedupe_artefacts --settings disclosures.settings.dev --permanent-links-db $DLROBOT_FOLDER/permalinks.dbm
   for host in $DEDUPE_HOSTS_SPACES; do
        scp $DLROBOT_FOLDER/permalinks.dbm $host:/tmp
        ssh $host git -C ~/smart_parser pull
        ssh $host touch /tmp/dlrobot_worker/.dlrobot_pit_stop
   done
   sleep 3h # till dlrobot worker stops
   parallel -a surname_spans.txt --jobs 2 --env DISCLOSURES_DB_HOST --env PYTHONPATH -S $DEDUPE_HOSTS --basefile $DEDUPE_MODEL  --verbose --workdir /tmp \
        python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --permanent-links-db /tmp/permalinks.dbm --dedupe-model-file $DEDUPE_MODEL  \
                --verbose 3  --threshold 0.9  --surname-bounds {} --write-to-db --settings disclosures.settings.dev --logfile dedupe.{}.log
                 

#12  Коммит статистики
   cd $TOOLS/disclosures_site
   python3 manage.py add_disclosures_statistics --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
   git commit -m "new statistics" data/statistics.json
   git push

#13
 cd $DLROBOT_FOLDER
 mysqldump -u disclosures -pdisclosures disclosures_db_dev  |  gzip -c > $DLROBOT_FOLDER/disclosures.sql.gz

#14 создание индексов для elasticsearch
   python3 $TOOLS/disclosures_site/manage.py search_index --rebuild  --settings disclosures.settings.dev -f

#15 создание sitemap (можно параллельно с индексированием elasticsearch)
  python3 $TOOLS/disclosures_site/manage.py generate_sitemaps --settings disclosures.settings.dev --output-folder sitemap

#16 go to prod (migalka), disclosures.ru is offline
    cd /var/www/smart_parser/tools/disclosures_site
    git pull

    # it takes more than 30 minutes  to unpack database, in future we have to use a temp databse
    # something like this (not tested yet)
    # todo: try to rename database with renaming all tables

    export DISCLOSURES_DATABASE_NAME=disclosures_prod_temp
    python3 manage.py create_database --settings disclosures.settings.prod --skip-checks
    zcat $DLROBOT_FOLDER/disclosures.sql.gz | mysql -u disclosures -pdisclosures -D $DISCLOSURES_DATABASE_NAME
    python3 manage.py elastic_manage --action backup-prod --settings disclosures.settings.dev
    python3 manage.py elastic_manage --action dev-to-prod --settings disclosures.settings.dev
    sudo systemctl restart disclosures
    sudo systemctl restart gunicorn.service
    # now prod works on database disclosures_prod_temp


    export DISCLOSURES_DATABASE_NAME=disclosures_db
    mysqladmin drop  $DISCLOSURES_DATABASE_NAME -u disclosures -pdisclosures
    python3 manage.py create_database --settings disclosures.settings.prod --skip-checks
    zcat $DLROBOT_FOLDER/disclosures.sql.gz | mysql -u disclosures -pdisclosures -D $DISCLOSURES_DATABASE_NAME
    sudo systemctl restart disclosures
    # now prod works on database disclosures_db

    mysqladmin drop  disclosures_prod_temp -u disclosures -pdisclosures


    # to rebuild one index
    #python3 manage.py search_index --rebuild  -f --settings disclosures.settings.dev --models declarations.Section

    # index sizes
    # curl 127.0.0.1:9200/_cat/indices

    # some query example
    #curl -X GET "localhost:9200/declaration_file_prod/_search?pretty" -H 'Content-Type: application/json' -d'{"query": {"match" : {"office_id" : 5963}}}'

#17 копируем файлы sitemap
    rm -rf disclosures/static/sitemap
    ln -s  $DLROBOT_FOLDER/sitemap disclosures/static/sitemap

#18  подменяем файл документов-исходников
     rm -rf disclosures/static/domains
     ln -s  $DLROBOT_FOLDER/$DISCLOSURES_FILES disclosures/static/domains


#19  посылаем данные dlrobot в каталог, который синхронизирутеся с облаком
    python3 $TOOLS/disclosures_site/scripts/send_source_documents_to_cloud.py  --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder $DLROBOT_CENTRAL_FOLDER"/processed_projects" --output-cloud-folder $YANDEX_DISK_FOLDER

