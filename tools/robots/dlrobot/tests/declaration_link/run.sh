DUMMY=$1
WEB_ADDR=$2
set -e
python3 test.py --web-addr $WEB_ADDR --start-page simple_doc/sved.html --found-links-count 1
python3 test.py --web-addr $WEB_ADDR --start-page other_website/sved.html --found-links-count 0
python3 test.py --web-addr $WEB_ADDR --start-page page_text/sved.html --found-links-count 1
python3 test.py --web-addr $WEB_ADDR --start-page arkvo/sved.html --found-links-count 41
