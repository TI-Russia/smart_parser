#ls tests/*.txt | xargs --verbose -n 1 -P 4 -I '{}'  python dlrobot.py --logfile temp  --rebuild  --project {} 
#ls tests/*.txt | xargs --verbose -n 1 -P 4  python dlrobot.py --logfile temp  --rebuild  --start-from last_step  --project 
#--skip-final-download

date

tests/*.txt.clicks.stats 

ls tests/*.txt | xargs --verbose -I '{}' -n 1 -P 5  \
   sh -c "python dlrobot.py --logfile temp  --rebuild  --project \"\$1\" "  -- {} 

git diff --exit-code tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi

date