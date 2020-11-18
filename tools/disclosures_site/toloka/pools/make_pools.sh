#!/usr/bin/env bash

# for converted assignment pools
if [ ! -d ../assignments ]; then
    mkdir ../assignments
fi 

ASSIGNMENTS_FILE=../assignments/assignments_test_pool_01_08-04-2019.tsv
DECLARATOR=~/declarator/transparency

## all declarator pools are in git branch toloka!!
python3 ../../manage.py import_declarator_toloka_pool \
  --input-pool $DECLARATOR/toloka/assignments/assignments_test_pool_01_08-04-2019.tsv \
  --output-pool $ASSIGNMENTS_FILE --settings disclosures.settings.prod

python3  $DECLARATOR/scripts/toloka_stats.py  $ASSIGNMENTS_FILE -u test_pool_u.tsv  -m test_pool_m.tsv

python3 ../../manage.py test_pool --test-pool  test_pool_m.tsv --dedupe-model-file $DECLARATOR/toloka/dedupe_model/dedupe.info --points-file points.txt --settings disclosures.settings.prod
