bash run_folder.sh $DECL_DOC_RECOGNIZER_LARGE_TESTS_FOLDER/many_plus many_plus
grep some_other_document many_plus/*.verdict > many_plus.metrics.txt
diff many_plus.metrics.txt many_plus.metrics.txt.canon
