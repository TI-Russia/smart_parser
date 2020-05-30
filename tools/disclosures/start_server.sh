#!/bin/bash
SCRIPT_FOLDER=`dirname $0`
cd $SCRIPT_FOLDER
source ../venv/bin/activate
export DJANGO_SETTINGS_MODULE=disclosures.settings.prod
python3 manage.py runserver 192.168.100.121:8000  --insecure --noreload

