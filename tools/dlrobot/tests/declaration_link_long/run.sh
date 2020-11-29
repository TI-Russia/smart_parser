DUMMY=$1
WEB_ADDR=$2
set -e
function check_folder() {
  local folder=$1
  python3 ../declaration_link/test.py --web-addr $WEB_ADDR --start-page $folder/sved.html | tr -d '\r' >  $folder.found_links
  git diff --exit-code $folder.found_links
}

check_folder admkrsk
