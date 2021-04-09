python3 ~/smart_parser/tools/source_doc_http/scripts/print_all_keys.py ~/declarator_hdd/Yandex.Disk/declarator/source_doc/bin_files >all_source_sha256.txt
export HOSTS="frontend,migalka,lena,avito"
JOBS_COUNT=4
#export SOURCE_DOC_SERVER_ADDRESS=migalka:8090
#export SMART_PARSER_SERVER_ADDRESS=migalka:8165
export SOURCE_DOC_SERVER_ADDRESS=192.168.100.26:8090
export SMART_PARSER_SERVER_ADDRESS=192.168.100.26:8165

parallel -a all_source_sha256.txt \
     --env SOURCE_DOC_SERVER_ADDRESS \
     --env ASPOSE_LIC \
     --env DECLARATOR_CONV_URL \
     --env SMART_PARSER_SERVER_ADDRESS \
     --env PYTHONPATH  \
     --jobs $JOBS_COUNT \
     -S $HOSTS  \
     --verbose \
     --workdir /tmp \
      python3 /home/sokirko/smart_parser/tools/smart_parser_http/scripts/rebuid_smart_parser_worker.py {}
