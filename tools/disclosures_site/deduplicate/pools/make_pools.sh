python3 ../../scripts/dedupe/make_pools.py

# sokirko assigned pools https://sandbox.toloka.yandex.ru/requester/project/15926/pool/611429
## and https://sandbox.toloka.yandex.ru/requester/project/15926/pool/608496, we make training and golden out of it

cd ../..

# create 20 training cases
python3 scripts/dedupe/create_golden.py --max-cases-number 20 --negative-ratio 50 --output-file deduplicate/pools/disclosures_training_20.tsv deduplicate/assignments/assignments_disclosures_golden_set_01.tsv  deduplicate/assignments/assignments_disclosures_golden_set.tsv

# create golden case
python3 scripts/dedupe/create_golden.py  --max-cases-number 1000 --output-file deduplicate/pools/disclosures_golden.tsv deduplicate/assignments/assignments_disclosures_golden_set_01.tsv  deduplicate/assignments/assignments_disclosures_golden_set.tsv
