portion=$1
if [ -z $1  ]; then
    echo "specify portion index"
    exit 1
fi


INPUT_FOLDER=/home/sokirko/declarator_hdd/declarator/2020-05-15/input_projects.$portion
RESULT_FOLDER=/home/sokirko/declarator_hdd/declarator/2020-05-15/processed_projects.$portion
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

