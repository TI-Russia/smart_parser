#!/usr/bin/env bash

python3 ../../manage.py train_on_pool --ml-model-file dedupe_new.info --train-pool   ../pools/train_pool_m.tsv --dedupe-train-recall 0.95 --use-random-forest --settings disclosures.settings.prod
python3 ../../manage.py test_pool  --test-pool  ../pools/test_pool_m.tsv  --dedupe-model-file dedupe_new.info --points-file  points_new.txt --settings disclosures.settings.prod
python3 ../../scripts/prec_recall_curve.py -s -p 0.97 points.txt points_new.txt

#if model is good
#cp dedupe_new.info dedupe.info
#cp points_new.txt points.txt
#git commit