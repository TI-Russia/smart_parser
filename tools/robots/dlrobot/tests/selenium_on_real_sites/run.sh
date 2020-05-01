python check_selenium.py --url http://www.mid.ru --anchor "противодействие" --target  "https://www.mid.ru/activity/corruption/general"

if [ $? != 0 ]; then
  #mid.ru is a wholly javascripted website
  echo "selenium does not work on mid.ru"
  exit 1
fi

python check_selenium.py --url http://aot.ru/docs/Nozhov/supplement1.pdf --download-folder download
if [ $? != 0 ]; then
  echo "download pdf failed"
  exit 1
fi

# I do not  know how to make selenium work for https://minvr.ru/press-center/collegium/5167/?doc=1
# since http header are application/octet-stream, but it a real html, so firefox won't open it, just timeouted for 5 minutes
#python check_selenium.py --url https://minvr.ru/press-center/collegium/5167/?doc=1 --download-folder download
#if [ $? != 0 ]; then
#  echo "download a file with content-type=application/octet-stream failed"
#  exit 1
#fi
