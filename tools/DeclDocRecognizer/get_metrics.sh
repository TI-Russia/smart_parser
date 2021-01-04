OUTPUT_METRICS=metrics.txt
bash run_folder.sh $DECL_DOC_RECOGNIZER_LARGE_TESTS_FOLDER/plus plus >/dev/null 2>/dev/null
echo "false negative:" >$OUTPUT_METRICS
/usr/bin/find plus -name '*.verdict' | xargs grep -L -E "(unknown_result)|(declaration_result)" >> $OUTPUT_METRICS


bash run_folder.sh $DECL_DOC_RECOGNIZER_LARGE_TESTS_FOLDER/minus minus >/dev/null 2>/dev/null
echo "false positives:" >> $OUTPUT_METRICS
/usr/bin/find minus -name '*.verdict' | xargs grep -L -E "(unknown_result)|(some_other_document_result)" >> $OUTPUT_METRICS

diff $OUTPUT_METRICS metrics.txt.canon