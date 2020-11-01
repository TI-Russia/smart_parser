SCRIPT_FOLDER=`dirname "$0"`

bash $SCRIPT_FOLDER/run_folder.sh $1
python3 $SCRIPT_FOLDER/filter_folder.py  --folder $1
