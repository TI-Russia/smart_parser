export DECLARATOR_HDD=/home/sokirko/declarator_hdd

HOSTS="migalka,oldtimer,lena"
HOSTS_SPACES=`echo $HOSTS | tr ',' ' '` 
#HOSTS=lena
#HOSTS="oldtimer"
export DECLARATOR_HDD=/home/sokirko/declarator_hdd
ROBOT_FOLDER=$DECLARATOR_HDD/declarator/2020-05-15
INPUT_FOLDER=$ROBOT_FOLDER/input_projects
PROCESSED_FOLDER=$ROBOT_FOLDER/processed_projects
[ -d $PROCESSED_FOLDER ] || mkdir $PROCESSED_FOLDER

for worker in $HOSTS_SPACES; do
    ping -c 1 $worker
    if [ $? != 0 ]; then
        echo "cannot ping $worker"
        exit 1
    fi
    scp initialize_worker.sh $worker:~
    ssh $worker "bash -x initialize_worker.sh $DECLARATOR_HDD"     
    if [ $? != 0 ]; then
        echo "initialize_worker fails on  $worker"
        exit 1
    fi
done



find $INPUT_FOLDER -type f  >files_to_process.txt
files_count=`wc -l files_to_process.txt`
echo "we are going to process $files_count files"

cat files_to_process.txt | \
    parallel  --verbose --joblog joblog.txt  \
              --sshdelay 1  --load 100% --jobs 4 -S $HOSTS --memfree 512M --retries 2 \
              --workdir ... bash -x $ROBOT_FOLDER/one_site.sh $PROCESSED_FOLDER
            

