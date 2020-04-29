# create a random.pdf and start pdf conversion task
PROJECT=$1
which soffice
if [ $? -ne 0 ]; then
	echo "cannot find soffice (libreoffice) in path"
	exit 1
fi

cd html
date +%Y%m%d%H%M%S >random.txt
soffice --headless --writer --convert-to "pdf" random.txt 
rm random.txt 
cd -


python ../../dlrobot.py --clear-cache-folder --project $PROJECT


files_count=`/usr/bin/find result -type f | wc -l`
if [ $files_count != 1 ]; then
    echo "no exported file found"
    exit 1
fi

conversion_tasks_count=`grep -c "register conversion task" dlrobot.log`
if [ $conversion_tasks_count != 1 ]; then
    echo "no conversion tasks found"
    exit 1
fi
