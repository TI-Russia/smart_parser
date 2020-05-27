INPUT_FOLDER=$1
RESULT_FOLDER=$2

if [ ! -d $INPUT_FOLDER ]; then
    echo "$INPUT_FOLDER does not exist"
    exit 1
fi

[ -d $RESULT_FOLDER ] || mkdir -p $RESULT_FOLDER

python3 ~/smart_parser/tools/robots/dlrobot/scripts/ubuntu_parallel/run_parallel.py --hosts migalka,lena,oldtimer,ventil \
    --log-file-name $RESULT_FOLDER/dlrobot_parallel.log --skip-already-processed \
    --result-folder $RESULT_FOLDER \
    --input-folder $INPUT_FOLDER \
    --pkey /home/sokirko/.ssh/id_rsa  > $RESULT_FOLDER/run_parallel.out  2>&1

