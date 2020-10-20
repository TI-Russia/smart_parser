BACKUP_HOST=converter2
BACKUP_HOST_FOLDER=/cygdrive/e/conv_db

scp C:/tmp/conv_db/converted_file_storage.json $BACKUP_HOST:$BACKUP_HOST_FOLDER

function copy_new_files() {
    local src=$1
    local dst=$2
    ls $src | /usr/bin/sort >a.1
    ssh $BACKUP_HOST "ls  $dst" > a.2
    join -v 1 a.1 a.2 >a.3
    tar --create --file a.tar -T a.3 -C $src
    rm a.1 a.2 a.3

    scp a.tar $BACKUP_HOST:$BACKUP_HOST_FOLDER
    rm a.tar
    ssh $BACKUP_HOST "cd $BACKUP_HOST_FOLDER; tar --file a.tar -C $dst --extract; rm a.tar"  
}

copy_new_files C:/tmp/conv_db/db_converted_files /cygdrive/e/conv_db/db_converted_files
copy_new_files D:/declarator/conv_db/db_input_files /cygdrive/e/conv_db/db_input_files
