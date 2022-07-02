  # Процесс создание базы disclosures = dlrobot+declarator (раз в месяц?)

#0 ~/smart_parser/tools/INSTALL.txt are prerequisites

set -e
COMMON_SCRIPT=~/smart_parser/tools/dlrobot/central/scripts/profile.sh
source $COMMON_SCRIPT


#1 создание нового каталога и файла настройки .profile
    cd $DLROBOT_UPDATES_FOLDER
    export OLD_DLROBOT_FOLDER=`find -mindepth 1 -maxdepth 1 -xtype d  | sort | tail -n 1 | xargs -n 1 realpath`
    # all projects that older than 5 hours in order not to get a race condition
    export CRAWL_EPOCH=`python3 -c "import time; print (int(time.time() - 60 * 5))"`
    export DLROBOT_FOLDER=$DLROBOT_UPDATES_FOLDER/$CRAWL_EPOCH

    mkdir -p $CRAWL_EPOCH
    cd $CRAWL_EPOCH
    echo "source $COMMON_SCRIPT" >.profile
    echo "" >> .profile
    echo "export DLROBOT_FOLDER=$DLROBOT_FOLDER" >> .profile
    echo "export CRAWL_EPOCH=$CRAWL_EPOCH" >> .profile
    echo "export OLD_DLROBOT_FOLDER=$OLD_DLROBOT_FOLDER" >> .profile
    source .profile

#2.  инициализация базы disclosures
    python3 $TOOLS/disclosures_site/manage.py create_database --settings disclosures.settings.dev --skip-checks

#3  слияние по файлам dlrobot, declarator  и старого disclosures, получение dlrobot_human.dbm
      python3 $TOOLS/dlrobot_human/scripts/join_human_and_dlrobot.py \
          --max-ctime $CRAWL_EPOCH \
          --input-dlrobot-folder  "$DLROBOT_CENTRAL_FOLDER/processed_projects" \
              --human-json $HUMAN_FILES_JSON \
          --old-dlrobot-human-json $OLD_DLROBOT_FOLDER/dlrobot_human.dbm \
          --output-json dlrobot_human.dbm

#4  предсказание office_id
    cd $DLROBOT_FOLDER
    python3 $TOOLS/predict_office/scripts/predict_office_dbm.py --dlrobot-human-path dlrobot_human.dbm

  #6  Копирование базы первичных ключей старой базы, чтобы поддерживать постоянство веб-ссылок по базе прод
     mv $OLD_DLROBOT_FOLDER/new_permalinks/* .
   # можно создать их прям сейчас
     #python3 $TOOLS/disclosures_site/manage.py create_permalink_storage --settings disclosures.settings.prod --directory $DLROBOT_FOLDER

  #9 (надо включить в import_json?)
      cd $DLROBOT_FOLDER # important
      python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev --directory $DLROBOT_FOLDER


  #10  Импорт json в dislosures_db (48 hours)
       python3 $TOOLS/disclosures_site/manage.py import_json \
                   --settings disclosures.settings.dev \
                   --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
                   --dlrobot-human dlrobot_human.dbm   \
                     --process-count 2  \
                     --permalinks-folder $DLROBOT_FOLDER

     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric source_document_count  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric sections_person_name_income_year_declarant_income_size  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
     python3 $TOOLS/disclosures_site/manage.py add_disclosures_statistics --check-metric sections_person_name_income_year_spouse_income_size  --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH

  #10.1  остановка dlrobot на $DEDUPE_HOSTS в параллель (максмимум 3 часа), может немного одновременно проработать со сливалкой
    echo "$DEDUPE_HOSTS" | xargs  --verbose -P 4 -n 1 python3 $TOOLS/dlrobot/worker/scripts/dl_cloud_manager.py --action stop --host &

  #11 создание surname_rank (40 мин)
    python3 $TOOLS/disclosures_site/manage.py build_surname_rank  --settings disclosures.settings.dev

  #12.  запуск сливалки, 1 gb memory each family basket, 30 GB temp files, no more than 2 processes per workstation
     #optional, if you have to run dedupe more than one time
     #python3 $TOOLS/disclosures_site/manage.py clear_dedupe_artefacts --settings disclosures.settings.dev

     #1 hour
     python3 $TOOLS/disclosures_site/manage.py copy_person_id --settings disclosures.settings.dev --permalinks-folder $DLROBOT_FOLDER

     python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs  --print-family-prefixes   --permalinks-folder $DLROBOT_FOLDER --settings disclosures.settings.dev > surname_spans.txt
     echo "$DEDUPE_HOSTS" | xargs  --verbose -P 4 -I {} -n 1 scp $DLROBOT_FOLDER/permalinks_declarations_person.dbm {}:/tmp

     #22 hours
     parallel --halt soon,fail=1 -a surname_spans.txt --jobs 3 --joblog parallel.log \
          --env DISCLOSURES_DB_HOST --env PYTHONPATH -S "$DEDUPE_HOSTS" --basefile $DEDUPE_MODEL  --verbose --workdir /tmp \
          python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --permalinks-folder /tmp --ml-model-file $DEDUPE_MODEL  \
                  --threshold 0.61  --surname-bounds {} --write-to-db --settings disclosures.settings.dev --logfile dedupe.{}.log

     if [ $? != "0" ]; then
       echo "dedupe failed on some cluster"
       exit 1
     fi
     python3 $TOOLS/disclosures_site/manage.py test_real_clustering_on_pool --test-pool $TOOLS/disclosures_site/deduplicate/pools/disclosures_test_m.tsv   --settings disclosures.settings.dev
     python3 $TOOLS/disclosures_site/manage.py external_link_surname_checker --fail-fast --links-input-file $TOOLS/disclosures_site/data/external_links.json  --settings disclosures.settings.dev
     if [ $? != "0" ]; then
       echo "Error! Some linked people are missing in the new db, web-links would be broken if we publish this db"
       exit 1
     fi
       python3 $TOOLS/disclosures_site/scripts/check_person_id_permanence.py --prod-db disclosures_db --dev-db disclosures_db_dev

#12.1 запускаем обратно dlrobot_worker
  echo "$DEDUPE_HOSTS" | xargs  --verbose -P 4 -n 1 python3 $TOOLS/dlrobot/worker/scripts/dl_cloud_manager.py --action start --host &

#13  Коммит статистики
   cd $TOOLS/disclosures_site
   git pull origin master
   python3 manage.py add_disclosures_statistics --settings disclosures.settings.dev --crawl-epoch $CRAWL_EPOCH
   git commit -m "new statistics" data/statistics.json ../dlrobot/central/data/dlrobot_remote_calls.dat
   git push

#13.1
cd $DLROBOT_FOLDER
python3 $TOOLS/disclosures_site/manage.py create_permalink_storage --settings disclosures.settings.dev --directory $DLROBOT_FOLDER/new_permalinks &
new_permalinks_pid=$!

#14 построение пола (gender)
   cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/manage.py build_genders --settings disclosures.settings.dev

#15 создание рейтингов
    python3 $TOOLS/disclosures_site/manage.py build_ratings --settings disclosures.settings.dev

#16 построение дополнительных параметров ведомств (calculated_params)
    python3 $TOOLS/disclosures_site/manage.py build_office_calculated_params --settings disclosures.settings.dev
    git -C $TOOLS/office_db/data/office_current commit -m "new office report"
    git -C $TOOLS/office_db/data/office_current add *.txt *.csv
    git -C $TOOLS/office_db/data/office_current push origin master

#17.1 build access logs squeeze
    cd $DLROBOT_FOLDER
    python3 $TOOLS/disclosures_site/scripts/access_log_squeeze.py --action build_popular_site_pages \
      --access-log-folder $ACCESS_LOG_ARCHIVE --output-path access_log_squeeze.txt

#17.2 update person redirects and filter access logs
    python3 $TOOLS/disclosures_site/manage.py update_person_redirects  --settings disclosures.settings.dev \
              --input-access-log-squeeze  access_log_squeeze.txt --output-access-log-squeeze access_log_squeeze_flt.txt

#17.3 sitemaps
    python3 $TOOLS/disclosures_site/manage.py generate_sitemaps --settings disclosures.settings.prod --output-file disclosures/static/sitemap.xml \
       --access-log-squeeze access_log_squeeze_flt.txt --tar-path sitemap.tar

#17.4 misspell dict
    mkdir $DLROBOT_FOLDER/misspell_bin
    cp $TOOLS/disclosures_site/data/misspell_bin/project.mwz  $TOOLS/disclosures_site/data/misspell_bin/gramtab.tab $DLROBOT_FOLDER/misspell_bin
    python3 $TOOLS/disclosures_site/manage.py create_misspell_fio_db --settings disclosures.settings.dev --output-folder $DLROBOT_FOLDER/misspell_bin

#18 создание дампа базы
    cd $DLROBOT_FOLDER
    mysqldump -u disclosures -pdisclosures disclosures_db_dev  |  gzip -c > disclosures.sql.gz
    p=$YANDEX_DISK_FOLDER/dlrobot_updates/$CRAWL_EPOCH
    if [ ! -d  $p ]; then mkdir -p $p; fi
    cp disclosures.sql.gz $p

#18.1
    python3 $TOOLS/dlrobot/central/scripts/yandex_disk.py --action sync --exclude-dirs declarator/source_doc --wait
    python3 $TOOLS/dlrobot/central/scripts/yandex_disk.py --action publish_special \
        --cloud-path declarator/dlrobot_updates//$CRAWL_EPOCH/disclosures.sql.gz --report-output-file full_sql_dump.html
    scp full_sql_dump.html $FRONTEND:$FRONTEND_WEB_SITE/declarations/templates/statistics

wait $new_permalinks_pid

#19  switch dev to  prod in backend (migalka)
    mysqladmin drop  disclosures_db -u disclosures -pdisclosures -f
    cd $TOOLS/disclosures_site
    bash $TOOLS/disclosures_site/scripts/rename_db.sh disclosures_db_dev disclosures_db
    sudo systemctl start elasticsearch
    python3 $TOOLS/disclosures_site/manage.py build_elastic_index --settings disclosures.settings.prod


#20 make binary archives and copy to frontend
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

    scp $DLROBOT_FOLDER/sitemap.tar $FRONTEND:/tmp/sitemap.tar

    ssh $FRONTEND rm -rf /tmp/misspell_bin
    scp -r $DLROBOT_FOLDER/misspell_bin $FRONTEND:/tmp

#21 обновление prod
    v1=`sudo mysqld --version`
    v2=`sudo /usr/share/elasticsearch/bin/elasticsearch --version`
    # реально следующие две строки (выкатки исходников и переключение) не работают автоматичеси,
    # тесты не проходят по таймаутам в бизнес-тайм,
    # а разворачивание всегда ломается. Приходится делать руками.
    ssh $FRONTEND python3 $FRONTEND_WEB_SITE/scripts/setup_head_version.py --mysql-version "\"$v1\"" --elasticsearch-version "\"$v2\""
    ssh $FRONTEND python3 $FRONTEND_WEB_SITE/scripts/switch_prod.py --mysql-tar /tmp/mysql.tar.gz \
      --elasticsearch-tar /tmp/elastic.tar.gz --sitemap-tar /tmp/sitemap.tar --misspell-folder /tmp/misspell_bin
      ssh $PROD_SOURCE_DOC_SERVER sudo systemctl restart source_declaration_doc

#22  посылаем данные dlrobot в каталог, который синхронизируется с облаком, очищаем dlrobot_central (без возврата)
    cd $DLROBOT_FOLDER
    python3 $TOOLS/dlrobot/central/scripts/send_dlrobot_projects_to_cloud.py  \
        --processed-projects-folder $DLROBOT_CENTRAL_FOLDER"/processed_projects" \
        --update-folder $DLROBOT_FOLDER \
        --output-cloud-folder $YANDEX_DISK_FOLDER/dlrobot_updates

