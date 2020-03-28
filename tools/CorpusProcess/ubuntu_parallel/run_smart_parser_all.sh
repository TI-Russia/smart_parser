HOSTS="migalka,oldtimer,ventil"
#HOSTS=migalka
INPUT_FOLDER=/home/sokirko/declarator_hdd/declarator/2020-02-01/
FOLDER_PROCESSOR=/home/sokirko/declarator_hdd/declarator/smart_parser_one_folder.sh

find $INPUT_FOLDER -type d  | grep -v '/$' | parallel --jobs 5 -S $HOSTS  bash -x $FOLDER_PROCESSOR
