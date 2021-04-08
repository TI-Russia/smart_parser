python3 ~/smart_parser/tools/source_doc_http/scripts/print_all_keys.py ~/declarator_hdd/Yandex.Disk/declarator/source_doc >all_source_sha256.txt
HOSTS="frontend"
JOBS_COUNT=1
export SOURCE_DOC_SERVER_ADDRESS=migalka:8090
export SMART_PARSER_SERVER_ADDRESS=migalka:8165

parallel -a all_source_sha256.txt \
     --env SOURCE_DOC_SERVER_ADDRESS \
     --env SMART_PARSER_SERVER_ADDRESS \
     --env PYTHONPATH  \
     --jobs $JOBS_COUNT \
     -S $HOSTS  \
     --verbose \
     --workdir /tmp \
      python3 /home/sokirko/smart_parser/tools/smart_parser_http/scripts/rebuid_smart_parser_worker.py {}
