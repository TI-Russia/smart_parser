set -e

COMMON_SCRIPT=$(dirname $0)/profile.sh
source $COMMON_SCRIPT


#======================================================================
#======== Обновление ручной базы (declarator), раз в квартал?  ========
#=====================================================================
#2.1 построение базы declarator:
    cd ~
    git clone sokirko@bitbucket.org:TI-Russia/declarator.git
    cd declarator/trasparency
    pip3 install -r ../deploy/requirements.txt
    mysqladmin drop  declarator -u db_creator -p$DB_CREATOR_PASSWORD -f
    echo "CREATE DATABASE declarator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    create user if not exists 'declarator'@ identified by 'declarator';
    GRANT ALL PRIVILEGES ON *.* TO 'declarator'@;" | mysql -u db_creator -p=$DB_CREATOR_PASSWORD
    cd ~/declarator_hdd/tmp/declarator

    #посмотреть https://declarator.org/manage/dump_files/ и скачать свежий дамп, например
    wget https://declarator.org/manage/dump_files/prod20201208_c2e1d1df8952449082527780429c0068.zip
    # zcat prod20201208_c2e1d1df8952449082527780429c0068.zip | mysql -D declarator -u declarator -pdeclarator
    # zcat стал выдавать ошибку gzip: prod20201208_c2e1d1df8952449082527780429c0068.zip: invalid compressed data--length error
    # а unzip не выдает
    unzip prod20201208_c2e1d1df8952449082527780429c0068.zip
    cat prod20201208.sql  | mysql -D declarator -u declarator -pdeclarator


#2.2  получить все новые (!) файлы из declarator и создать файл human_files.json
    cp $HUMAN_FILES_JSON $HUMAN_FILES_JSON.sav
    python3 $TOOLS/disclosures_site/scripts/export_human_files.py --table declarations_documentfile  --dlrobot-human-json $HUMAN_FILES_JSON

#2.3 создание ручных json (было опционально, я сейчас перестал это делать, поскольку там неполные json)
#    [ -d  $HUMAN_JSONS_FOLDER ] || mkdir $HUMAN_JSONS_FOLDER
#    cd ~/declarator/transparency
#    source ../venv/bin/activate
#    python3 manage.py export_in_smart_parser_format --output-folder $HUMAN_JSONS_FOLDER

#2.4 Ручное обновление офисов
  echo  "select * from declarator.declarations_office  where id not in (select id from disclosures_db.declarations_office)" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator > new_offices.txt
  #take new_offices.txt and add it to disclosures_site/data/web_site_snapshots.txt
