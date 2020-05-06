date

rm regression_tests/*.txt.clicks.stats tests/*.txt.clicks

# do not set -P 5, because firefox can crush
ls regression_tests/*.txt | xargs --verbose -I '{}' -n 1 -P 5  \
   sh -c "python3 dlrobot.py --logfile \"\$1\".log  --project \"\$1\" "  -- {}

git diff --exit-code regression_tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi

date

