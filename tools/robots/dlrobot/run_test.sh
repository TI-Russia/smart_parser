ls tests/*.txt | xargs --verbose -n 1 -P 4 -I '{}' python dlrobot.py --rebuild  --step  last_step --project tests/{} 
git diff tests