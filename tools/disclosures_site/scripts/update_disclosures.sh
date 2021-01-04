u
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

    mkdir -p $CRAWL_EPOCH
    cd $CRAWL_EPOCH
    cp $TOOLS/disclosures_site/scripts/update_common.sh  .profile
    echo "" >> .profile
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
        --output-json dlrobot_human.json


#3  получение статистики по dlrobot_human.json, сравнение с предыдущим обходом
    python3 $TOOLS/disclosures_site/scripts/dlrobot_human_stats.py dlrobot_human.json > dlrobot_human.json.stats
    new_size=$(stat -c%s "dlrobot_human.json")
    old_size=$(stat -c%s "$OLD_DLROBOT_FOLDER/dlrobot_human.json")
    if (( $old_size > $new_size )); then
        echo "the size of dlrobot_human.json is less than the size of older one, check dlrobot_human.json.stats"
        exit 1
    endif


#7  Создание базы первичных ключей старой базы, чтобы поддерживать постоянство веб-ссылок по базе прод
   python3 $TOOLS_PROD/manage.py create_permalink_storage --settings disclosures.settings.prod --output-dbm-file permalinks.dbm


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

   #15 hours
   python3 $TOOLS/disclosures_site/manage.py import_json \
               --settings disclosures.settings.dev \
               --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
               --dlrobot-human dlrobot_human.json   \
               --process-count 2  \
               --permanent-links-db permalinks.dbm

   python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric source_document_count  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
   python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric sections_count  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH


#11 создание surname_rank
python3 $TOOLS/disclosures_site/manage.py build_surname_rank  --settings disclosures.settings.dev


#12.  запуск сливалки, 4 gb memory each family portion, 30 GB temp files, no more than one process per workstation
   #optional, clear person table
   python3 $TOOLS/disclosures_site/manage.py clear_dedupe_artefacts --settings disclosures.settings.dev

   #1 hour
   python3 $TOOLS/disclosures_site/manage.py copy_person_id --settings disclosures.settings.dev --permanent-links-db permalinks.dbm

   python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs  --print-family-prefixes   --permanent-links-db $DLROBOT_FOLDER/permalinks.dbm --settings disclosures.settings.dev > surname_spans.txt
   echo $DEDUPE_HOSTS_SPACES | tr " " "\n"  | xargs  --verbose -P 4 -I {} -n 1 scp $DLROBOT_FOLDER/permalinks.dbm {}:/tmp
   echo $DEDUPE_HOSTS_SPACES | tr " " "\n"  | xargs  --verbose -P 4 -n 1 python3 $TOOLS/dlrobot_server/git_update_cloud_worker.py --action stop --host

   #18 hours
   parallel -a surname_spans.txt --jobs 2 --env DISCLOSURES_DB_HOST --env PYTHONPATH -S $DEDUPE_HOSTS --basefile $DEDUPE_MODEL  --verbose --workdir /tmp \
        python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --permanent-links-db /tmp/permalinks.dbm --ml-model-file $DEDUPE_MODEL  \
                --threshold 0.61  --surname-bounds {} --write-to-db --settings disclosures.settings.dev --logfile dedupe.{}.log

   python3 $TOOLS/disclosures_site/manage.py test_real_clustering_on_pool --test-pool $TOOLS/disclosures_site/deduplicate/pools/disclosures_test_m.tsv   --settings disclosures.settings.dev

#13  Коммит статистики
   cd $TOOLS/disclosures_site
   git pull
   python3 manage.py add_disclosures_statistics --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
   git commit -m "new statistics" data/statistics.json
   git push

#14 создание индекса для elasticsearch, создание sitemap   в фоновом режиме
   {
     python3 $TOOLS/disclosures_site/manage.py search_index --rebuild  --settings disclosures.settings.dev -f
     cd $DLROBOT_FOLDER
     python3 $TOOLS/disclosures_site/manage.py generate_static_sections --settings disclosures.settings.dev --output-folder sections
   } &
   ELASTIC_PID=$!


#16 создание дампа базы
 cd $DLROBOT_FOLDER
 mysqldump -u disclosures -pdisclosures disclosures_db_dev  |  gzip -c > $DLROBOT_FOLDER/disclosures.sql.gz

#17 обновление prod
    wait $ELASTIC_PID
    cd $TOOLS_PROD
    git pull

    export DISCLOSURES_DATABASE_NAME=disclosures_prod_temp
    python3 manage.py create_database --settings disclosures.settings.prod --skip-checks
    zcat $DLROBOT_FOLDER/disclosures.sql.gz | mysql -u disclosures -pdisclosures -D $DISCLOSURES_DATABASE_NAME
    python3 manage.py elastic_manage --action backup-prod --settings disclosures.settings.dev
    python3 manage.py elastic_manage --action dev-to-prod --settings disclosures.settings.dev
    sudo systemctl restart gunicorn
    # now prod works on database disclosures_prod_temp


    export DISCLOSURES_DATABASE_NAME=disclosures_db
    mysqladmin drop  $DISCLOSURES_DATABASE_NAME -u disclosures -pdisclosures -f
    python3 manage.py create_database --settings disclosures.settings.prod --skip-checks
    zcat $DLROBOT_FOLDER/disclosures.sql.gz | mysql -u disclosures -pdisclosures -D $DISCLOSURES_DATABASE_NAME
    sudo systemctl restart gunicorn
    # now prod works on database disclosures_db

    mysqladmin drop  disclosures_prod_temp -u disclosures -pdisclosures -f

#18 копируем файлы sitemap
    rm -rf disclosures/static/sections
    ln -s  $DLROBOT_FOLDER/sections disclosures/static/sections
    rm -rf disclosures/static/sitemap.xml
    python3 manage.py generate_sitemaps --settings disclosures.settings.prod --output-file disclosures/static/sitemap.xml

#19  посылаем данные dlrobot в каталог, который синхронизирутеся с облаком, очищаем dlrobot_central (без возврата)
    cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/scripts/send_dlrobot_projects_to_cloud.py  --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder $DLROBOT_CENTRAL_FOLDER"/processed_projects" --output-cloud-folder $YANDEX_DISK_FOLDER

