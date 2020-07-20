INPUT_FOLDER=$1
HOSTS=$2
FOLDER_PROCESSOR=~/smart_parser/tools/CorpusProcess/ubuntu_parallel/smart_parser_one_folder.sh
JOBS_PER_WORKER=5

find $INPUT_FOLDER -mindepth 1 -maxdepth 1  -type d| parallel --verbose --jobs $JOBS_PER_WORKER -S $HOSTS  bash -x $FOLDER_PROCESSOR
