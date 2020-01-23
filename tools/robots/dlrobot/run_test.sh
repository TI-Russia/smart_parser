#ls tests/*.txt | xargs --verbose -n 1 -P 4 -I '{}'  python dlrobot.py --logfile temp  --rebuild  --project {} 
#ls tests/*.txt | xargs --verbose -n 1 -P 4  python dlrobot.py --logfile temp  --rebuild  --start-from last_step  --project 
#--skip-final-download

date

tests/*.txt.clicks.stats 

ls tests/*.txt | xargs --verbose -I '{}' -n 1 -P 5  \
   sh -c "python dlrobot.py --logfile temp  --project \"\$1\" "  -- {} 

git diff --exit-code tests 2>/dev/null
if [ $? -eq 0 ]; then
    echo  "==== TESTS PASSED ====="!
else
    echo  "==== TESTS FAILED ====="!
fi

date


# prin sum
#git diff mil.txt.clicks.stats  | grep -E '^[+-]\s+[0-9]' | gawk 'BEGIN{sum=0}{print; if ($1 == "-") {sum -= $2} else {sum += $2} print sum}' 
