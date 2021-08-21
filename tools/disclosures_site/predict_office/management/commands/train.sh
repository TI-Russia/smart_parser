FOLDER=~/tmp/predict_office/tf.00
mkdir -p $FOLDER

# create train and test from declarator data
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action build_office_train_set  --input-file dlrobot_human.dbm --predict-office-pool  office_declarator_pool.txt
scp office_declarator_pool.txt dev_machine:$FOLDER


# create a pool for toloka
shuf cases_to_predict_dump.txt  | grep -v 'service.nalog.ru' | grep -v '{"title": "", "roles": [], "departments": []' | head -n 200 |  sort >pool200a.txt.s
cut -f 1  pool200a.txt.s >a.1
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action select --sha256-list-file a.1  --input-file dlrobot_human.dbm --output-file a.dbm
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action to_json  --input-file a.dbm --output-file a.dbm | jq -rc '.documents | to_entries[] | [.key, .value.office_id] | @tsv' | sort >a.sha_office
join -t $'\t' pool200a.txt.s  a.sha_office  | awk -F "\t" -v  OFS="\t" '{print $1,$2,$5,$4}' >pool200a.txt
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_toloka --model-folder model --test-pool pool200a.txt --toloka-output-pool toloka.txt
# go to toloka, add a new pool, access it, download results
cat ~/Downloads/assignments_from_pool_962392__20-08-2021.tsv | cut -f 1,8 | grep -v 'INPUT:sha256' | sort  >a
cat ~/smart_parser/tools/disclosures_site/predict_office/pools/pool????.txt  | sort   join -t $'\t' - a -o '1.1,1.2,2.2,1.4' >p.txt
cp p.txt ~/smart_parser/tools/disclosures_site/predict_office/pools/pool200a.txt


#on dev machine
cd $FOLDER
python3 ~/smart_parser/tools/disclosures_site/manage.py build_office_index --settings disclosures.settings.prod
python3 ~/smart_parser/tools/disclosures_site/manage.py prepare_office_pool --declarator-pool ../office_declarator_pool.txt \
   --real-pool  ~/smart_parser/tools/disclosures_site/predict_office/pools/pool400.txt --real-pool-add-count  6 \
    --train-pool train_pool.txt
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_train --model-folder model  --train-pool train_pool.txt --epoch-count  17
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_test --test-pool ~/smart_parser/tools/disclosures_site/predict_office/pools/pool100.txt  --bigrams-path office_ngrams.txt  --model-folder model --threshold 0.95 0.99

