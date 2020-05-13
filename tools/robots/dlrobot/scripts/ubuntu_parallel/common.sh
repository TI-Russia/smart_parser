export DECLARATOR_HDD=/home/sokirko/declarator_hdd

function setup_declarator_hdd() {
    echo "setup_declarator_hdd"
    [ -d $DECLARATOR_HDD ] || mkdir $DECLARATOR_HDD
    echo "files_count  in $DECLARATOR_HDD"
    files_count=`ls $DECLARATOR_HDD | wc -l`
    if [ $files_count  == "0" ];  then
        sshfs migalka:/mnt/sdb $DECLARATOR_HDD
    fi
}

