date

rm tests/*.txt.clicks.stats 

ls tests/*.txt | xargs --verbose -I '{}' -n 1 -P 5  \
   sh -c "python dlrobot.py --logfile \"\$1\".log  --project \"\$1\" "  -- {}

git diff --exit-code tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi

date

