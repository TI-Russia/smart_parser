bash run_folder.sh $DeclDocRecognizerLargeTestsFolder/plus >/dev/null 2>/dev/null
echo "false negative:"
/usr/bin/find $DeclDocRecognizerLargeTestsFolder/plus -name '*.verdict' | xargs grep -L -E "(unknown_result)|(declaration_result)"


bash run_folder.sh $DeclDocRecognizerLargeTestsFolder/minus >/dev/null 2>/dev/null
echo "false positives:"
/usr/bin/find $DeclDocRecognizerLargeTestsFolder/minus -name '*.verdict' | xargs grep -L -E "(unknown_result)|(some_other_document_result)"
