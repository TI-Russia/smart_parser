ls tests/*.txt | xargs --verbose -n 1 -P 4 -I '{}'  python dlrobot.py --rebuild  --project {} 
git diff tests 2>/dev/null
