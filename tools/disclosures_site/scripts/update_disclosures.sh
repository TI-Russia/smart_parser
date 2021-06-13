# Процесс создание базы disclosures = dlrobot+declarator (раз в месяц?)

#0 ~/smart_parser/tools/INSTALL.txt are prerequisites

set -e
SOURCE_ROOT=~/smart_parser/tools/disclosures_site
COMMON_SCRIPT=$SOURCE_ROOT/scripts/update_common.sh
source $COMMON_SCRIPT


#1 создание нового каталога и файла настройки .profile
    cd $DLROBOT_UPDATES_FOLDER/
    export OLD_DLROBOT_FOLDER=`find -mindepth 1 -maxdepth 1 -xtype d  | sort | tail -n 1 | xargs -n 1 realpath`
    # all projects that older than 5 hours in order not to get a race condition
    export CRAWL_EPOCH=`python3 -c "import time; print (int(time.time() - 60 * 5))"`
    export DLROBOT_FOLDER=$DLROBOT_UPDATES_FOLDER/$CRAWL_EPOCH

    mkdir -p $CRAWL_EPOCH
    cd $CRAWL_EPOCH
    cp $COMMON_SCRIPT .profile
    echo "" >> .profile
    echo "" >> .profile
    echo "export DLROBOT_FOLDER=$DLROBOT_FOLDER" >> .profile
    echo "export CRAWL_EPOCH=$CRAWL_EPOCH" >> .profile
    echo "export OLD_DLROBOT_FOLDER=$OLD_DLROBOT_FOLDER" >> .profile
    source .profile

    cp $DLROBOT_CENTRAL_FOLDER/dlrobot_central.log $YANDEX_DISK_FOLDER/dlrobot_updates

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


#7  Создание базы первичных ключей старой базы, чтобы поддерживать постоянство веб-ссылок по базе прод (1 час)
   python3 $TOOLS/disclosures_site/manage.py create_permalink_storage --settings disclosures.settings.prod --directory $DLROBOT_FOLDER


#8.  инициализация базы disclosures
    python3 $TOOLS/disclosures_site/manage.py create_database --settings disclosures.settings.dev --skip-checks --username db_creator --password root
    python3 $TOOLS/disclosures_site/manage.py makemigrations --settings disclosures.settings.dev
    python3 $TOOLS/disclosures_site/manage.py migrate --settings disclosures.settings.dev
    python3 $TOOLS/disclosures_site/manage.py test $TOOLS/disclosures_site/declarations/tests --settings disclosures.settings.dev

#9 (надо включить в import_json?)
    cd $DLROBOT_FOLDER # im portant
    python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev --directory $DLROBOT_FOLDER


#10  Импорт json в dislosures_db (32 hours)
     python3 $TOOLS/disclosures_site/manage.py import_json \
                 --settings disclosures.settings.dev \
                 --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
                 --dlrobot-human dlrobot_human.json   \
                 --process-count 3  \
                 --permalinks-folder $DLROBOT_FOLDER

     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric source_document_count  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric sections_person_name_income_year_declarant_income_size  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric sections_person_name_income_year_spouse_income_size  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH

#10.1  остановка dlrobot на $DEDUPE_HOSTS в параллель (максмимум 3 часа), может немного одновременно проработать со сливалкой
echo $DEDUPE_HOSTS | tr "," "\n"  | xargs  --verbose -P 4 -n 1 python3 $TOOLS/dlrobot_server/scripts/git_update_cloud_worker.py --action stop --host &

#11 создание surname_rank (40 мин)
  python3 $TOOLS/disclosures_site/manage.py build_surname_rank  --settings disclosures.settings.dev

  #12.  запуск сливалки, 4 gb memory each family portion, 30 GB temp files, no more than one process per workstation
     #optional, if you have to run dedupe more than one time
     #python3 $TOOLS/disclosures_site/manage.py clear_dedupe_artefacts --settings disclosures.settings.dev

     #1 hour
     python3 $TOOLS/disclosures_site/manage.py copy_person_id --settings disclosures.settings.dev --permalinks-folder $DLROBOT_FOLDER

     python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs  --print-family-prefixes   --permalinks-folder $DLROBOT_FOLDER --settings disclosures.settings.dev > surname_spans.txt
     echo $DEDUPE_HOSTS | tr "," "\n"  | xargs  --verbose -P 4 -I {} -n 1 scp $DLROBOT_FOLDER/permalinks_declarations_person.dbm {}:/tmp

     #22 hours
     parallel --halt soon,fail=1 -a surname_spans.txt --jobs 2 --env DISCLOSURES_DB_HOST --env PYTHONPATH -S $DEDUPE_HOSTS --basefile $DEDUPE_MODEL  --verbose --workdir /tmp \
          python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --permalinks-folder /tmp --ml-model-file $DEDUPE_MODEL  \
                  --threshold 0.61  --surname-bounds {} --write-to-db --settings disclosures.settings.dev --logfile dedupe.{}.log

     if [ $? != "0" ]; then
       echo "dedupe failed on some cluster"
       exit 1
     fi
     python3 $TOOLS/disclosures_site/manage.py test_real_clustering_on_pool --test-pool $TOOLS/disclosures_site/deduplicate/pools/disclosures_test_m.tsv   --settings disclosures.settings.dev
     python3 $TOOLS/disclosures_site/manage.py external_link_surname_checker --links-input-file $TOOLS/disclosures_site/data/external_links.json  --settings disclosures.settings.dev
     if [ $? != "0" ]; then
       echo "Error! Some linked people are missing in the new db, web-links would be broken if we publish this db"
       exit 1
     fi
     python3 $TOOLS/disclosures_site/scripts/check_person_id_permanence.py disclosures_db disclosures_db_dev

#12.1 запускаем обратно dlrobot_worker
echo $DEDUPE_HOSTS | tr "," "\n"  | xargs  --verbose -P 4 -n 1 python3 $TOOLS/dlrobot_server/scripts/git_update_cloud_worker.py --action start --host &

#13  Коммит статистики
   cd $TOOLS/disclosures_site
   git pull
   python3 manage.py add_disclosures_statistics --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
   git commit -m "new statistics" data/statistics.json ../web_site_db/data/dlrobot_remote_calls.dat
   git push

#14 построение пола (gender)
   cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/manage.py build_genders --settings disclosures.settings.dev


#15 создание рейтингов
    python3 $TOOLS/disclosures_site/manage.py build_ratings --settings disclosures.settings.dev

#16 создание дампа базы (для debug)
    cd $DLROBOT_FOLDER
    mysqldump -u disclosures -pdisclosures disclosures_db_dev  |  gzip -c > $DLROBOT_FOLDER/disclosures.sql.gz


#17 switch dev to  prod in backend (migalka)
    mysqladmin drop  disclosures_db -u disclosures -pdisclosures -f
    cd $TOOLS/disclosures_site
    bash scripts/rename_db.sh disclosures_db_dev disclosures_db
    sudo systemctl start elasticsearch
    python3 manage.py build_elastic_index --settings disclosures.settings.prod

#18 sitemaps
    cd $TOOLS/disclosures_site
    python3 manage.py generate_sitemaps --settings disclosures.settings.prod --output-file disclosures/static/sitemap.xml \
      --access-log-folder $ACCESS_LOG_ARCHIVE --tar-path sitemap.tar
    scp sitemap.tar $FRONTEND:/tmp/sitemap.tar

#19 make binary archives and copy to frontend
    sudo systemctl stop mysql
    sudo chmod a+rwx /var/lib/mysql
    cd /var/lib/mysql
    sudo find * -maxdepth 0 -type f | cat -  <( sudo find sys performance_schema mysql disclosures_db) | sudo xargs tar cfvz $DLROBOT_FOLDER/mysql.tar.gz
    cd $DLROBOT_FOLDER
    scp $DLROBOT_FOLDER/mysql.tar.gz $FRONTEND:/tmp
    sudo systemctl start mysql

    sudo systemctl stop elasticsearch
    sudo tar --create --file $DLROBOT_FOLDER/elastic.tar.gz --gzip  --directory /var/lib/elasticsearch   .
    scp $DLROBOT_FOLDER/elastic.tar.gz $FRONTEND:/tmp
    sudo systemctl start elasticsearch

#20 обновление prod
    elastic_search_version_prod=`ssh $FRONTEND sudo /usr/share/elasticsearch/bin/elasticsearch --version`
    elastic_search_version_central=`sudo /usr/share/elasticsearch/bin/elasticsearch --version`
    if [ "$elastic_search_version_prod" != "$elastic_search_version_central" ]; then
      echo "Error! Elasticsearch version in the central server and in the prod server are different. Binary indices can be incompatible!"
      exit 1
    fi
    mysql_version_prod=`ssh $FRONTEND sudo mysqld --version`
    mysql_version_central=`sudo mysqld --version`
    if [ "$mysql_version_prod" != "$mysql_version_central" ]; then
      echo "Error! Mysql version in the central server and in the prod server are different. Binary indices can be incompatible!"
      exit 1
    fi

    ssh $FRONTEND git -C ~/smart_parser pull
    ssh $FRONTEND bash -x /home/sokirko/smart_parser/tools/disclosures_site/scripts/switch_prod.sh /tmp/mysql.tar.gz /tmp/elastic.tar.gz /tmp/sitemap.tar
    ssh $PROD_SOURCE_DOC_SERVER sudo systemctl restart source_declaration_doc

#21  посылаем данные dlrobot в каталог, который синхронизирутеся с облаком, очищаем dlrobot_central (без возврата)
    cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/scripts/send_dlrobot_projects_to_cloud.py  --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder $DLROBOT_CENTRAL_FOLDER"/processed_projects" --output-cloud-folder $YANDEX_DISK_FOLDER/dlrobot_updates

