TEST_FOLDER=tests
rm  $TEST_FOLDER/*.json
for x in `ls $TEST_FOLDER`; do
    python dlrecognizer.py --source-file $TEST_FOLDER/$x  --output $TEST_FOLDER/$x.json
done
git diff $TEST_FOLDER
