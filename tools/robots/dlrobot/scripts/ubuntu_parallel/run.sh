#HOSTS="migalka,oldtimer,lena"
HOSTS=lena
export DECLARATOR_HDD=/home/sokirko/declarator_hdd
[ -d $DECLARATOR_HDD ] || mkdir $DECLARATOR_HDD
files_count=`ls $DECLARATOR_HDD | wc -l`
if [ $files_count  == "0" ];  then
    sshfs migalka:/mnt/sdb $DECLARATOR_HDD
fi
ROBOT_FOLDER=$DECLARATOR_HDD/declarator/2020-05-15
INPUT_FOLDER=$ROBOT_FOLDER/input_projects
PROCESSED_FOLDER=$ROBOT_FOLDER/processed_projects

function process_one_file() {
    local project_file=$1
    local basename_project_file=`basename $project_file`
    local folder=${basename_project_file%.txt} 
    echo 'process $project_file'
    mkdir $folder
    mv $project_file $folder
    cd $folder
    python3 /home/sokirko/smart_parser/tools/robots/dlrobot/dlrobot.py --project  $basename_project_file
    rm -rf cached
    cd -
    mv $folder $PROCESSED_FOLDER
}

export -f process_one_file
export PROCESSED_FOLDER

find $INPUT_FOLDER -type f >files_to_process.txt
files_count=`wc -l files_to_process.txt`
echo "we are going to process $files_count files"
cat files_to_process.txt | \
    parallel  --env PROCESSED_FOLDER --env my_func --env process_one_file --verbose --sshdelay 1  --jobs 5 -S $HOSTS  \
        --workdir ... process_one_file

