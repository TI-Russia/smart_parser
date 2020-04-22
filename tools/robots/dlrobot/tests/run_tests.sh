echo "do not run these tests if production dlrobot is executing on this workstation!"
tests=`/usr/bin/find . -maxdepth 1 -mindepth 1 -type d`
for test_folder in $tests; do
  echo -n "test $test_folder -> "
  cd $test_folder
  [ ! -f test_log.out ] || rm test_log.out
  bash -x run.sh >test_log.out 2>&1
  if [ $? -eq 0 ]; then
     echo "success"
  else
     echo "failed"
     exit 1
  fi
  cd - >/dev/null
done
