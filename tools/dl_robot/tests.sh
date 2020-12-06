set -e
find tests/ | grep tests/test_ | xargs --verbose -n 1 -P 10 python3 -m unittest --failfast

if [ $? -ne 0 ]; then
  echo "tests failed"
fi    