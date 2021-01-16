#BACKUP_FOLDER=Z:/conv_db
BACKUP_FOLDER=\\\\CONVERTER2\\E\\conv_db
LOG=copy_to_server.log

function copy_larger_files() {
    local src=$1
    local dst=$2
    for f in `ls $src`; do
      src_size=`stat --printf="%s" $src/$f`
      if [ ! -f $dst/$f ]; then
        echo "cp $src/$f $dst (a new file)" >> $LOG
        cp $src/$f $dst
      else
        dst_size=`stat --printf="%s" $dst/$f`
        if [ $src_size  -gt  $dst_size ]; then
          echo "cp $src/$f $dst (size is greater)" >> $LOG
          cp $src/$f $dst
        fi
      fi
    done
}

echo "copy started" >> $LOG
date >> $LOG
copy_larger_files C:/tmp/conv_db/db_converted_files $BACKUP_FOLDER/db_converted_files
copy_larger_files D:/declarator/conv_db/db_input_files $BACKUP_FOLDER/db_input_files
echo "all done" >> $LOG
