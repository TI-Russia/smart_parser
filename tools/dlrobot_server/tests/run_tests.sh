PROCESS_COUNT=1
TESTS=""

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
      -p|--process-count)
          PROCESS_COUNT="$2"
          shift
          shift
          ;;
      *)
          TESTS="$TESTS $1"
          shift
          ;;
  esac
done

if [ -z "$TESTS" ]; then
   TESTS=`/usr/bin/find . -maxdepth 1 -mindepth 1 -type d`
fi

echo "run $TESTS in $PROCESS_COUNT threads"

PORT=8390

for test_folder in $TESTS; do
  all_tests="$all_tests $test_folder $PORT"
  PORT=$((PORT+1))
done

rm -rf failed_tests.txt

echo $all_tests | xargs -P $PROCESS_COUNT -n 2 --verbose bash run_one_test.sh

if [ -f failed_tests.txt ]; then
    echo "failed tests:"
    cat failed_tests.txt
    rm failed_tests.txt
fi
