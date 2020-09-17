python3 check_search_engine.py

if [ $? != 0 ]; then
    echo "google banned us, captcha?"
    exit 1
fi

python3 check_search_engine.py --prefer-russian-search-engine

if [ $? != 0 ]; then
    echo "yandex banned us, captcha?"
    exit 1
fi
