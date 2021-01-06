bash run_regression_tests.sh

#test files for metrics calculation are saved to sokirko's yandex disk because they are too large for github
export DECL_DOC_RECOGNIZER_TESTS_FOLDER=/mnt/ntfs/Sokirko/declarator_test_files/DeclDocRecognizer

bash get_metrics.sh $DECL_DOC_RECOGNIZER_TESTS_FOLDER/plus $DECL_DOC_RECOGNIZER_TESTS_FOLDER/minus metrics.txt
bash get_metrics.sh $DECL_DOC_RECOGNIZER_TESTS_FOLDER/many_plus "" many_plus.metrics.txt

