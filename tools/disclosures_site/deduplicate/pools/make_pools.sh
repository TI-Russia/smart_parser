python3 ../../scripts/dedupe/make_pools.py

# create golden and training from https://sandbox.toloka.yandex.ru/requester/project/15926/pool/611429
# and https://sandbox.toloka.yandex.ru/requester/project/15926/pool/608496
cd ../..
python3 scripts/dedupe/create_golden.py --negative-ratio 50 --output-file deduplicate/pools/disclosures_golden_and_training.tsv deduplicate/assignments/assignments_disclosures_golden_set_01.tsv  deduplicate/assignments/assignments_disclosures_golden_set.tsv
