set -e
export HUMAN_FILES=human_files.dbm
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
  --document-file-id 33594  --table declarations_documentfile  --dlrobot-human-json $HUMAN_FILES

#mkdir -p processed_projects/dogm.mos.ru
#cd processed_projects/dogm.mos.ru
#python3 $TOOLS/robots/dlrobot/dl_robot.py --project dogm.mos.ru.txt
python3 $TOOLS/source_doc_http/source_doc_client.py --action put --walk-folder-recursive processed_projects/dogm.mos.ru/result
python3 $TOOLS/smart_parser_http/smart_parser_client.py --action put --walk-folder-recursive processed_projects/dogm.mos.ru/result
sleep 2m


python3 $TOOLS/disclosures_site/scripts/join_human_and_dlrobot.py \
        --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder  processed_projects \
        --human-json $HUMAN_FILES \
        --output-json dlrobot_human.dbm


python3 $TOOLS/disclosures_site/manage.py create_database --settings disclosures.settings.dev --username db_creator --password root --skip-checks
python3 $TOOLS/disclosures_site/manage.py makemigrations --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py migrate --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py create_permalink_storage  --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py clear_database --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py predict_office --dlrobot-human-path dlrobot_human.dbm

python3 $TOOLS/disclosures_site/manage.py import_json \
               --settings disclosures.settings.dev \
               --smart-parser-human-json-folder $HUMAN_JSONS_FOLDER \
               --dlrobot-human dlrobot_human.dbm   \
               --process-count 1  \
               --permalinks-folder .

python3 $TOOLS/disclosures_site/manage.py copy_person_id \
        --settings disclosures.settings.dev \
        --permalinks-folder .

export DEDUPE_MODEL=$TOOLS/disclosures_site/deduplicate/model/random_forest.pickle
python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --ml-model-file $DEDUPE_MODEL  --threshold 0.61 --write-to-db --settings disclosures.settings.dev --permalinks-folder .

python3 $TOOLS/disclosures_site/manage.py build_genders --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py build_ratings --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py build_office_calculated_params --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py build_elastic_index --settings disclosures.settings.dev
