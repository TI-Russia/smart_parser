DLROBOT_FOLDER=~/declarator_hdd/declarator/2020-02-01
SCRIPT_FOLDER=~/smart_parser/tools/robots
DOMAINS_FOLDER=domains
ALL_HUMAN_FILES_FOLDER=out.documentfile

cd $DLROBOT_FOLDER


#download all human files
python3 $SCRIPT_FOLDER/download_all_documents.py --table declarations_documentfile --output-folder $ALL_HUMAN_FILES_FOLDER

#create sha256 for all human files and store to human_files.json
python $SCRIPT_FOLDER/create_json_by_human_files.py --folder $ALL_HUMAN_FILES_FOLDER --table declarations_documentfile --output-json human_files.json

# copy missing human files to folder domains
python $SCRIPT_FOLDER/join_human_and_dlrobot.py --dlrobot-folder $DOMAINS_FOLDER --human-json human_files.json --output-json dlrobot_human.json
