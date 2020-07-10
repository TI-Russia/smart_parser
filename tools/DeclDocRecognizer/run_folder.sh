FOLDER=$1
rm $FOLDER/*.verdict
ls $FOLDER  | grep -v ".txt$" | xargs --verbose -n 1 -P 5 -I {} python dlrecognizer.py --keep-txt --reuse-txt --source-file $FOLDER/{}
