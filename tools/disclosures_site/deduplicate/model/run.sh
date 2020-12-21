python3 ../../manage.py train_ml_on_pool --settings disclosures.settings.prod --train-pool ../pools/disclosures_train_m.tsv
python3 ../../manage.py test_ml_on_pool  --settings disclosures.settings.prod --test-pool ../pools/disclosures_test_m.tsv  --ml-model-file random_forest.pickle --points-file points.txt.new
python3 ../../scripts/dedupe/prec_recall_curve.py -s -p 0.97  points.txt points.txt.new