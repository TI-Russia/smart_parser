INPUT_FOLDER=$1
HOSTS=$2
FOLDER_PROCESSOR=~/smart_parser/tools/CorpusProcess/ubuntu_parallel/smart_parser_one_folder.sh
JOBS_PER_WORKER=5

find $INPUT_FOLDER -type d -mindepth 1 -maxdepth 1 | xargs  -n 1 realpath | parallel --verbose --jobs $JOBS_PER_WORKER -S $HOSTS  bash -x $FOLDER_PROCESSOR