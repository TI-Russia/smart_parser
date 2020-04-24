echo "do not run these tests if production dlrobot is executing on this workstation, we are gonna to kill all firefox instances!"
taskkill /F  /IM firefox.exe

tests=`/usr/bin/find . -maxdepth 1 -mindepth 1 -type d `
PORT=8190

for test_folder in $tests; do
  bash run_one_test.sh $test_folder $PORT &
  PORT=$((PORT+1))
  sleep 2  #otherwise firefox at start is too slow
done

wait