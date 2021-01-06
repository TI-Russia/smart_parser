TEST_FOLDER=tests
rm  $TEST_FOLDER/*.verdict
for x in `ls $TEST_FOLDER`; do
    python3 dlrecognizer.py --source-file $TEST_FOLDER/$x  --output-verdict $TEST_FOLDER/$x.verdict
done
git diff $TEST_FOLDER
