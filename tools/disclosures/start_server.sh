#!/bin/bash
SCRIPT_FOLDER=`dirname $0`
cd $SCRIPT_FOLDER
source ../venv/bin/activate
python3 manage.py runserver 192.168.100.121:8000  --insecure --noreload

