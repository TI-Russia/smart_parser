python3 check_search_engine.py --search-engine-id 0

if [ $? != 0 ]; then
    echo "google banned us, captcha?"
    exit 1
fi

python3 check_search_engine.py --search-engine-id 1

if [ $? != 0 ]; then
    echo "yandex banned us, captcha?"
    exit 1
fi

python3 check_search_engine.py --search-engine-id 2

if [ $? != 0 ]; then
    echo "bing banned us, captcha?"
    exit 1
fi
