bash run_tests.sh

#test files are saved to sokirko's yandex disk (because they are too large for github)
export DECL_DOC_RECOGNIZER_LARGE_TESTS_FOLDER=/mnt/ntfs/Sokirko/declarator_test_files/DeclDocRecognizer

bash get_metrics.sh
bash get_metrics_large.sh

