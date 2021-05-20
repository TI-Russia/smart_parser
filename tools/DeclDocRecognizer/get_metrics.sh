PLUS_FOLDER=$1
MINUS_FOLDER=$2
OUTPUT_METRICS=$3
PLUS_FOLDER_TMP=`basename "$PLUS_FOLDER"`
MINUS_FOLDER_TMP=`basename "$MINUS_FOLDER"`

if [ -n "$PLUS_FOLDER" ]; then
  bash run_folder.sh $PLUS_FOLDER $PLUS_FOLDER_TMP >/dev/null 2>/dev/null
  echo "false negative:" >$OUTPUT_METRICS
  grep some_other_document $PLUS_FOLDER_TMP/*.verdict >> $OUTPUT_METRICS
fi

if [ -n "$MINUS_FOLDER" ]; then
  bash run_folder.sh $MINUS_FOLDER $MINUS_FOLDER_TMP >/dev/null 2>/dev/null
  echo "false positives:" >> $OUTPUT_METRICS
  grep declaration_result $MINUS_FOLDER_TMP/*.verdict >> $OUTPUT_METRICS
fi

diff $OUTPUT_METRICS $OUTPUT_METRICS.canon