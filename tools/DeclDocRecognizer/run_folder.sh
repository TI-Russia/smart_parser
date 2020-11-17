FOLDER=$1
rm $FOLDER/*.json.verdict
rm $FOLDER/*.verdict
ls $FOLDER  | grep -v ".txt$" | xargs --verbose -n 1 -P 5 -I {} python3  dlrecognizer.py --keep-txt --reuse-txt --source-file $FOLDER/{}
