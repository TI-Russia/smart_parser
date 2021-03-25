FOLDER=$1
OUTPUT_FOLDER=$2
rm $OUTPUT_FOLDER/*.verdict
ls $FOLDER  | grep -v ".txt$" | xargs --verbose -n 1 -P 5 -I {} \
  python3  dlrecognizer.py --keep-txt --reuse-txt --source-file $FOLDER/{} --output-folder $OUTPUT_FOLDER
