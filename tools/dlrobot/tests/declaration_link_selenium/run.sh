DUMMY=$1
WEB_ADDR=$2
set -e

python3 test.py --start-page https://www.mkrf.ru/activities/reports/index.php --project mkrf.txt >  $folder.found_links

