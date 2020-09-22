DUMMY=$1
WEB_ADDR=$2
set -e
function check_folder() {
  local folder=$1
  python3 test.py --web-addr $WEB_ADDR --start-page $folder/sved.html >  $folder.found_links
  #git diff --exit-code $folder.found_links
  git diff $folder.found_links
}

check_folder simple_doc
check_folder other_website
check_folder page_text
check_folder arkvo
check_folder admkrsk
