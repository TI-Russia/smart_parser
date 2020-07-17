#!/bin/bash
SCRIPT_FOLDER=`dirname $0`
DISCLOSURES_FOLDER=`realpath $SCRIPT_FOLDER/../..`
cd $DISCLOSURES_FOLDER
export PYTHONPATH=$DISCLOSURES_FOLDER:$DISCLOSURES_FOLDER/..
source ../venv/bin/activate
python3 manage.py runserver 192.168.100.151:8000  --insecure --noreload --settings disclosures.settings.prod &

