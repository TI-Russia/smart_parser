FOLDER=$1
rm $FOLDER/*.json
ls $FOLDER  | xargs --verbose -n 1 -P 5 -I {} python dlrecognizer.py --keep-txt --reuse-txt --source-file $FOLDER/{}
