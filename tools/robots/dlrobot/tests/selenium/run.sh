python check_selenium.py http://www.mid.ru "противодействие" "https://www.mid.ru/activity/corruption/general"

if [ $? != 0 ]; then
    echo "selenium does not work"
    exit 1
fi

