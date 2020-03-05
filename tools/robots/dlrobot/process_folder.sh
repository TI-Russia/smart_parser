# do not set -P 5, because firefox can crush
if [[ -z "$ASPOSE_LIC" ]]; then 
    echo "set ASPOSE_LIC before run smart_parser"
    exit 1
fi

if [[ ! -d cached ]]; then
    mkdir cached # otherwise race condition
fi 

if [[ ! -d cached/search_engine_requests ]]; then
    mkdir cached/search_engine_requests # otherwise race condition
fi 
 

pkill firefox

# too many files left after calibre convertor
rm -rf /tmp/calibre*


ls $1/*.txt | xargs --verbose -I '{}' -n 1 -P 4  \
   sh -c "python3 dlrobot.py --logfile \"\$1\".log  --project \"\$1\" "  -- {}
