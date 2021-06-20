set -e
export SOURCE_DOC_SERVER_ADDRESS=migalka:8090
export SMART_PARSER_SERVER_ADDRESS=migalka:8165
export HOSTS="samsung,migalka,lena,avito"
JOBS_COUNT=4

#rebuild the new version on migalka
mkdir ~/tmp/rebuild_smart_parser
cd ~/tmp/rebuild_smart_parser
git -C ~/smart_parser pull
dotnet build --no-incremental  -c Release  ~/smart_parser/
dotnet test  -c Release  ~/smart_parser/
~/smart_parser/src/bin/Release/netcoreapp3.1/smart_parser -version


#restart smart_parser server to let it know the new version of smart_parser
pkill -f  smart_parser_server.py
cd ~/declarator_hdd/declarator/smart_parser_server
rm nohup.out; nohup bash -x run.sh &
cd -

#restart source_doc_server
pkill -f source_doc_server.py
python3 ~/smart_parser/tools/source_doc_http/scripts/print_all_keys.py ~/declarator_hdd/Yandex.Disk/declarator/source_doc/bin_files >all_source_sha256.txt
cd ~/declarator_hdd/Yandex.Disk/declarator/source_doc
rm nohup.out; nohup bash -x run.sh &
cd -


#rebuild smart_parser on workers
echo -n $HOSTS | xargs -d , -n 1 -I {} ssh {} git -C ~/smart_parser pull
echo -n $HOSTS | xargs -P 4 -d , -n 1 -I {} --verbose ssh {} dotnet build --no-incremental  -c Release  ~/smart_parser/
echo -n $HOSTS | xargs -P 4 -d , -n 1 -I {} --verbose ssh {} ~/smart_parser/src/bin/Release/netcoreapp3.1/smart_parser -version


#check servers are running
pong=`curl http://$SOURCE_DOC_SERVER_ADDRESS/ping`
if [ "$pong" != "pong" ]; then
  echo "source server does not answer"
fi

pong=`curl http://$SMART_PARSER_SERVER_ADDRESS/ping`
if [ "$pong" != "pong" ]; then
  echo "smart parser server does not answer"
fi

yes=`curl http://$DECLARATOR_CONV_URL/ping`
if [ "$yes" != "yes" ]; then
  echo "conversion server does not answer"
fi


#start processing
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
