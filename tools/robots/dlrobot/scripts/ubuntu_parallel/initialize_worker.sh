DECLARATOR_HDD=$1

echo "setup_declarator_hdd"
[ -d $DECLARATOR_HDD ] || mkdir $DECLARATOR_HDD
echo "files_count  in $DECLARATOR_HDD"
files_count=`ls $DECLARATOR_HDD | wc -l`
if [ $files_count  == "0" ];  then
   sshfs migalka:/mnt/sdb $DECLARATOR_HDD
    if [ $? != 0 ]; then
        echo "cannot setup declaration_hdd"
        exit 1
    fi
fi

pkill -f firefox
if [ ! -f /home/sokirko/smart_parser/tools/robots/dlrobot/dlrobot.py  ]; then
    echo "cannot find dlrobot.py"
    exit 1
fi

free_disk_bytes_kb=`df . --output=avail | tail -n 1`
if [ $free_disk_bytes_kb -le 1048576  ]; then
    echo "at least 1GB free disk space must be available"
    exit 1
fi

cd /home/sokirko/smart_parser
git pull
if [ $? != 0 ]; then
    echo "cannot run git pull"
    exit 1
fi


