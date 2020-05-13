source $(dirname $0)/common.sh

HOSTS="migalka,oldtimer,lena"
#HOSTS=lena
#HOSTS="oldtimer"
export DECLARATOR_HDD=/home/sokirko/declarator_hdd
ROBOT_FOLDER=$DECLARATOR_HDD/declarator/2020-05-15
INPUT_FOLDER=$ROBOT_FOLDER/input_projects
PROCESSED_FOLDER=$ROBOT_FOLDER/processed_projects
[ -d $PROCESSED_FOLDER ] || mkdir $PROCESSED_FOLDER

setup_declarator_hdd

find $INPUT_FOLDER -type f  >files_to_process.txt
files_count=`wc -l files_to_process.txt`
echo "we are going to process $files_count files"

cat files_to_process.txt | \
    parallel  --verbose --joblog joblog.txt  \
              --sshdelay 1  --load 100% --jobs 4 -S $HOSTS --memfree 512M --retries 1 \
              --workdir ... bash -x $ROBOT_FOLDER/one_site.sh $PROCESSED_FOLDER
            

