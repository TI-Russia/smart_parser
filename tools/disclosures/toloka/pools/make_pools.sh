#!/usr/bin/env bash

ASSIGNMENTS_FILE=../assignments/assignments_test_pool_01_08-04-2019.tsv
DECLARATOR=~/declarator/transparency

#python ../../manage.py import_declarator_toloka_pool \
#  --input-pool $DECLARATOR/toloka/assignments/assignments_test_pool_01_08-04-2019.tsv \
#  --output-pool $ASSIGNMENTS_FILE

python  $DECLARATOR/scripts/toloka_stats.py  $ASSIGNMENTS_FILE -u test_pool_u.tsv  -m test_pool_m.tsv

python ../../manage.py test_pool --test-pool  test_pool_m.tsv --dedupe-model-file $DECLARATOR/toloka/dedupe_model/dedupe.info --points-file points.txt
