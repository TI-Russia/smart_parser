python3 check_selenium.py \
    --url http://www.mid.ru  \
    --start-anchor "противодействие"  \
    --assert-child-url "https://www.mid.ru/activity/corruption/general"

if [ $? != 0 ]; then
  #mid.ru is a wholly javascripted website
  echo "selenium does not work on mid.ru"
  exit 1
fi


python3 check_selenium.py --url http://aot.ru/docs/Nozhov/supplement1.pdf --download-folder download
if [ $? != 0 ]; then
  echo "download pdf failed"
  exit 1
fi

# example to ajax adding search results while scrolling the page down
python3 check_selenium.py   --url "https://minpromtorg.gov.ru/search_results/?date_from_38=&date_to_38=&q_38=%D0%B8%D0%BC%D1%83%D1%89%D0%B5%D1%81%D1%82%D0%B2%D0%BE&sortby_38=date&sources_38%5B%5D=contents_news%2Ccontents_documents_list%2Ccontents_documents_list_file%2Ccontents_files_list%2Ccontents_npa%2Ccontents_person%2Ccontents_dep%2Ccontents_regions%2Ccontents_text%2Ccontents_list&source_id_38=1&spec_filter_38%5B%5D=" --check-scroll-down

if [ $? != 0 ]; then
  echo "minpromtorg.gov.ru failed"
  exit 1
fi

python3 check_selenium.py \
 --start-anchor "загрузить" \
  --url "http://adm.ugorsk.ru/about/vacancies/information_about_income/?SECTION_ID=5244&ELEMENT_ID=79278"

if [ $? != 0 ]; then
  echo "adm.ugorsk.ru failed"
  exit 1
fi

# I do not  know how to make selenium work for https://minvr.ru/press-center/collegium/5167/?doc=1
# since http header are application/octet-stream, but it a real html, so firefox won't open it, just timeouted for 5 minutes
#python check_selenium.py --url https://minvr.ru/press-center/collegium/5167/?doc=1 --download-folder download
#if [ $? != 0 ]; then
#  echo "download a file with content-type=application/octet-stream failed"
#  exit 1
#fi
