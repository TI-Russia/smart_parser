date

rm regression_tests/*.txt.clicks.stats regression_tests/*.txt.clicks regression_tests/*.txt.log

ls regression_tests/*.txt | xargs --verbose -n 1 -P 5 python3 dlrobot.py --project

git diff --exit-code regression_tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi

date

