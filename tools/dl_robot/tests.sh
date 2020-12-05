set -e
for tests in `ls test_*.py`; do
  module="${filename%.*}"
  python3 -m unittest tests.$module
  break
done