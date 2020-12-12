set -e
export HUMAN_FILES_JSON=human_files.json
export HUMAN_JSONS_FOLDER=humans_jsons.dummy
export SMART_PARSER_SERVER_ADDRESS=localhost:8165
export SOURCE_DOC_SERVER_ADDRESS=localhost:8090
export TOOLS=~/smart_parser/tools

rm -rf $HUMAN_JSONS_FOLDER
mkdir $HUMAN_JSONS_FOLDER
export CRAWL_EPOCH=2147483647 # far future (2038 year)
host=`hostname`
if [ $host  == "migalka" ]; then
  echo "do not start this script on a production server"
  exit 1
fi

function start_smart_parser_server() {
  echo "delete  smart parser service"
  set +e
  pkill -f smart_parser_server
  set -e
  local workdir=smart_parser_server
  rm -rf $workdir
  mkdir $workdir
  cd $workdir
  python3 $TOOLS/smart_parser_http/smart_parser_server.py &
  SMART_PARSER_PID=$!
  cd -
}

function start_source_doc_server() {
  echo "delete  source doc server"
  set +e
  pkill -f source_doc_server
  set -e
  local workdir=source_doc_server
  rm -rf $workdir
  mkdir $workdir
  python3 $TOOLS/source_doc_http/source_doc_server.py --data-folder $workdir &
  SOURCE_DOC_SERVER_PID=$!
}

rm -rf *.log

start_smart_parser_server

start_source_doc_server

sleep 2

python3 $TOOLS/disclosures_site/scripts/export_human_files.py --start-from-an-empty-file \
  --document-file-id 33594  --table declarations_documentfile  --dlrobot-human-json $HUMAN_FILES_JSON

#mkdir -p processed_projects/dogm.mos.ru
#cd processed_projects/dogm.mos.ru
#python3 $TOOLS/robots/dlrobot/dlrobot.py --project dogm.mos.ru.txt
python3 $TOOLS/source_doc_http/source_doc_client.py --action put --walk-folder-recursive processed_projects/dogm.mos.ru/result
python3 $TOOLS/smart_parser_http/smart_parser_client.py --action put --walk-folder-recursive processed_projects/dogm.mos.ru/result
sleep 2m


python3 $TOOLS/disclosures_site/scripts/join_human_and_dlrobot.py \
        --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder  processed_projects \
        --human-json $HUMAN_FILES_JSON \
        --output-json dlrobot_human.json


sudo python3 $TOOLS/disclosures_site/manage.py create_database --settings disclosures.settings.dev --password root --skip-checks
python3 $TOOLS/disclosures_site/manage.py makemigrations --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py migrate --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py create_permalink_storage  --settings disclosures.settings.dev --output-dbm-file permalinks.dbm
python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev --permanent-links-db permalinks.dbm
python3 $TOOLS/disclosures_site/manage.py clear_database --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py import_json \
               --settings disclosures.settings.dev \
               --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
               --dlrobot-human dlrobot_human.json   \
               --process-count 1  \
               --permanent-links-db permalinks.dbm

python3 $TOOLS/disclosures_site/manage.py copy_person_id \
        --settings disclosures.settings.dev \
        --permanent-links-db permalinks.dbm

export DEDUPE_MODEL=~/declarator/transparency/toloka/dedupe_model/dedupe.info
python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --write-to-db --settings disclosures.settings.dev --permanent-links-db permalinks.dbm

python3 $TOOLS/disclosures_site/manage.py search_index --rebuild  --settings disclosures.settings.dev -f
