BACKUP_HOST=migalka
BACKUP_FOLDER=/mnt/sdb/Yandex.Disk/declarator/conv_db
LOG=copy_to_server.log
RSYNC="rsync -v -r -e \"/bin/ssh\" --size-only"

echo "copy started" >> $LOG
date >> $LOG

$RSYNC /cygdrive/c/tmp/conv_db/access.log $BACKUP_HOST:$BACKUP_FOLDER  >> $LOG
$RSYNC /cygdrive/c/tmp/conv_db/converted_file_storage.json  $BACKUP_HOST:$BACKUP_FOLDER  >> $LOG
$RSYNC /cygdrive/c/tmp/conv_db/db_converted_files $BACKUP_HOST:$BACKUP_FOLDER  >> $LOG

#too much space (more than 500 GB)
#$RSYNC /cygdrive/d/declarator/conv_db/db_input_files $BACKUP_HOST:$BACKUP_FOLDER   >> $LOG

date >> $LOG
echo "all done" >> $LOG
