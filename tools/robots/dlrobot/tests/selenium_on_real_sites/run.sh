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
python3 check_selenium.py \
    --start-anchor "сведения" \
    --url "http://minpromtorg.gov.ru/search_results/index.php?q_24=имущество&sources_24%5B0%5D=group_documents&source_id_24=1&aj_24=1&from_18=19#-1"

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
