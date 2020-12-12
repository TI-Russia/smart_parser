export HUMAN_FILES_JSON=human_files.json

export TOOLS=~/smart_parser/tools
export DISCLOSURES_FILES=domains

rm -rf humans_json.dummy
mkdir humans_jsons.dummy
export CRAWL_EPOCH=2147483647 # far future (2038 year)
export SMART_PARSER_SERVER_ADDRESS=localhost:9178

echo "delete  smart parser service"
pkill -f smart_parser_cache

rm *.log
#python3 $TOOLS/disclosures_site/scripts/export_human_files.py --document-file-id 33594  --table declarations_documentfile  --output-json $HUMAN_FILES_JSON

#mkdir -p processed_projects/dogm.mos.ru
#cd processed_projects/dogm.mos.ru
#python3 $TOOLS/robots/dlrobot/dlrobot.py --project dogm.mos.ru.txt

python3 $TOOLS/disclosures_site/scripts/join_human_and_dlrobot.py \
        --max-ctime $CRAWL_EPOCH \
        --input-dlrobot-folder  processed_projects \
        --human-json $HUMAN_FILES_JSON \
        --output-domains-folder $DISCLOSURES_FILES \
        --output-json dlrobot_human.json

rm -rf smart_parser_cache
mkdir smart_parser_cache
cd smart_parser_cache
python3 $TOOLS/robots/dlrobot/scripts/cloud/smart_parser_cache.py &
SMART_PARSER_PID=$!
cd -
sleep 10s

python3 $TOOLS/robots/dlrobot/scripts/cloud/smart_parser_cache_client.py --action put --walk-folder-recursive $DISCLOSURES_FILES
sleep 1m

sudo python3 $TOOLS/disclosures_site/manage.py create_database --settings disclosures.settings.dev --password root --skip-checks
python3 $TOOLS/disclosures_site/manage.py makemigrations --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py migrate --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py create_permalink_storage  --settings disclosures.settings.dev --output-dbm-file permalinks.dbm
python3 $TOOLS/disclosures_site/manage.py create_sql_sequences  --settings disclosures.settings.dev --permanent-links-db permalinks.dbm
python3 $TOOLS/disclosures_site/manage.py clear_database --settings disclosures.settings.dev
python3 $TOOLS/disclosures_site/manage.py import_json \
               --settings disclosures.settings.dev \
               --smart-parser-human-json-folder humans_jsons.dummy \
               --dlrobot-human dlrobot_human.json   \
               --process-count 1  \
               --permanent-links-db permalinks.dbm

python3 $TOOLS/disclosures_site/manage.py copy_person_id \
        --settings disclosures.settings.dev \
        --permanent-links-db permalinks.dbm

export DEDUPE_MODEL=~/declarator/transparency/toloka/dedupe_model/dedupe.info
python3 $TOOLS/disclosures_site/manage.py generate_dedupe_pairs --dedupe-model-file $DEDUPE_MODEL --verbose 3  --threshold 0.9  --write-to-db --settings disclosures.settings.dev --permanent-links-db permalinks.dbm

python3 $TOOLS/disclosures_site/manage.py search_index --rebuild  --settings disclosures.settings.dev -f
