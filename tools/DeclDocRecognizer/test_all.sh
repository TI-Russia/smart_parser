bash run_tests.sh

export DeclDocRecognizerLargeTestsFolder=/mnt/ntfs/tmp/smart_parser/smart_parser/tools/DeclDocRecognizer
bash get_metrics.sh >metrics.txt
diff metrics.txt metrics.txt.canon

bash run_folder.sh $DeclDocRecognizerLargeTestsFolder/many_plus
grep some_other_document $DeclDocRecognizerLargeTestsFolder/many_plus/*.verdict > many_plus.metrics.txt
diff many_plus.metrics.txt many_plus.metrics.txt.canon

