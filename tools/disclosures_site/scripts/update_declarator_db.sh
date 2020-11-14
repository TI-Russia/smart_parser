set -e

source $(dirname $0)/update_common.sh

#======================================================================
#======== Обновление ручной базы (declarator), раз в квартал?  ========
#=====================================================================
#2.1 построение базы declarator:
    cd ~
    git clone sokirko@bitbucket.org:TI-Russia/declarator.git
    cd declarator/trasparency
    pip3 install -r ../deploy/requirements.txt
    echo "CREATE DATABASE declarator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    create user if not exists 'declarator'@ identified by 'declarator';
    GRANT ALL PRIVILEGES ON *.* TO 'declarator'@;" | mysql
    #browse https://declarator.org/manage/dump_files/ и найти свежий дамп
    wget https://declarator.org/manage/dump_files/prod????.tar.gz
    zcat prod????.tar.gz | mysql -D declarator


#2.2  получить все новые (!) файлы из declarator в каталог $HUMAN_FILES_FOLDER и создать файл human_files.json
    python $TOOLS/disclosures_site/scripts/export_human_files.py --table declarations_documentfile --output-folder $HUMAN_FILES_FOLDER --output-json $HUMAN_FILES_JSON

#2.3  Отправляем все новые Pdf на конвертацию
    find $HUMAN_FILES_FOLDER -name '*.pdf' |  xargs --verbose -n 10  python $TOOLS/ConvStorage/scripts/convert_pdf.py --skip-receiving

#2.4 создание ручных json
    [ -d  $HUMAN_JSONS_FOLDER ] || mkdir $HUMAN_JSONS_FOLDER
    cd ~/declarator/transparency
    source ../venv/bin/activate
    python3 manage.py export_in_smart_parser_format --output-folder $HUMAN_JSONS_FOLDER
