TMP_FOLDER=tests_tmp_logs
if [ -d $TMP_FOLDER ]; then
  rm -rf $TMP_FOLDER;
fi
mkdir $TMP_FOLDER

cd tests
ls test_*.py | xargs --verbose -I {} -n 1 -P 8 bash -c "python3 -m unittest  -v {}  2>../$TMP_FOLDER/{}.err_log"
failed=$?
cd -

if [ $failed -ne 0 ]; then
  echo "tests failed"
  grep -E "(FAIL:)|(ERROR:)" $TMP_FOLDER/*.err_log
fi
