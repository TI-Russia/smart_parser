export http_proxy=http://91.197.3.66:24531/
export https_proxy=http://91.197.3.66:24531/
export no_proxy=localhost,0.0.0.0,127.0.0.0,127.0.1.1,127.0.1.1,192.168.100.151,local.home,c.disclosures.ru,127.0.0.1


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
