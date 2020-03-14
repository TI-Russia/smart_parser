python check_search_engine.py

if [ $? != 0 ]; then
    echo "google banned us, captcha?"
    exit 1
fi

