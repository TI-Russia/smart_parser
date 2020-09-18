if [ ! -z "$1" ]; then
   tests=$1
   echo "run only $tests"
else
   tests=`/usr/bin/find . -maxdepth 1 -mindepth 1 -type d`
fi

source ../delete_firefox_instances.sh

PORT=8190

for test_folder in $tests; do
  all_tests="$all_tests $test_folder $PORT"
  PORT=$((PORT+1))
done

rm -rf failed_tests.txt

echo $all_tests | xargs -P 3 -n 2 --verbose bash run_one_test.sh

if [ -f failed_tests.txt ]; then
    echo "failed tests:"
    cat failed_tests.txt
    rm failed_tests.txt
fi
