rm *.err_log

find tests/ -name '*.py' | grep tests/test_ | xargs --verbose -I {} -n 1 -P 10 python3 -m unittest  -v {}  2>{}.err_log

if [ $? -ne 0 ]; then
  echo "tests failed"
  grep "FAIL:' *.err_log
  
fi
