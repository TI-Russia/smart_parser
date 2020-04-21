FOLDER=$1
rm $FOLDER/*.json
rm $FOLDER/*.txt
ls $FOLDER  | xargs --verbose -n 1 -P 5 -I {} python dlrecognizer.py --source-file $FOLDER/{}
