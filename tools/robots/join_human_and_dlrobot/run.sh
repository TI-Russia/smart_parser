DLROBOT_FOLDER=~/declarator_hdd/declarator/2020-02-01
TOOLS_FOLDER=~/smart_parser/tools
DOMAINS_FOLDER=domains
ALL_HUMAN_FILES_FOLDER=out.documentfile

cd $DLROBOT_FOLDER

#download all human files
python3 $TOOLS_FOLDER/robots/join_human_and_dlrobot/download_all_documents.py --table declarations_documentfile --output-folder $ALL_HUMAN_FILES_FOLDER

#create sha256 for all human files and store to human_files.json
python $TOOLS_FOLDER/robots/join_human_and_dlrobot/create_json_by_human_files.py --folder $ALL_HUMAN_FILES_FOLDER --table declarations_documentfile --output-json human_files.json

# copy missing human files to folder domains
python $TOOLS_FOLDER/join_human_and_dlrobot.py --dlrobot-folder $DOMAINS_FOLDER --human-json human_files.json --output-json dlrobot_human.json

#build smart_parser json
cp $TOOLS_FOLDER/CorpusProcess/ubuntu_parallel/*.sh .
bash run_smart_parser_all.sh

#export smart_parser json from database
python ~/declarator/transparency/manage.py export_in_smart_parser_format  --output-folder human_smart_parser_jsons >export_in_smart_parser_format.log

#create dlrobot db
python $TOOLS_FOLDER/robots/join_human_and_dlrobot/create_dlrobotdb.py --smart-parser-human-json-folder human_smart_parser_jsons  --dlrobot-human dlrobot_human.json >create_dlrobotdb.log
