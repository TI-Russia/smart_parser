ls tests/*.txt | xargs --verbose -n 1 -P 4 -I '{}'  python dlrobot.py --logfile temp  --rebuild  --project {} 

git diff --exit-code tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi
