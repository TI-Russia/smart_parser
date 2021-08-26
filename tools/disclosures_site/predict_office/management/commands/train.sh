FOLDER=~/tmp/predict_office/tf.00
mkdir -p $FOLDER

# create train and test from declarator data
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action build_office_train_set  --input-file dlrobot_human.dbm --predict-office-pool  office_declarator_pool.txt
scp office_declarator_pool.txt dev_machine:$FOLDER

# refresh test and train pools on migalka, then copy it to developer notebook
cd ~/smart_parser/tools/disclosures_site/predict_office/pools
for src_file in *.source.txt; do
  output_file=${src_file%.source.txt}.txt
  echo "$src -> $output_file"
  python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py \
    --action rebuild_ml_pool \
    --input-file  ~/declarator_hdd/declarator/dlrobot_updates/1629223992/dlrobot_human.dbm \
    --input-predict-office-pool $src  \
    --output-predict-office-pool $output_file
done

# create a pool for toloka
cat cases_to_predict_dump.txt  | grep -v 'service.nalog.ru' | grep -v '{"title": "", "roles": [], "departments": []' | head -n 200 |  sort >pool.mos.ru.txt
cut -f 1  pool.mos.ru.txt >a.1
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action to_json  --sha256-list-file a.1 --input-file dlrobot_human.dbm | jq -rc '.documents | to_entries[] | [.key, .value.office_id] | @tsv' | sort >a.sha_office
join -t $'\t' pool.mos.ru.txt  a.sha_office  | awk -F "\t" -v  OFS="\t" '{print $1,$2,$5,$4}' >pool.mos.ru.txt.with_office_id
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_toloka --model-folder model --test-pool pool200a.txt --toloka-output-pool toloka.txt

# go to toloka, add a new pool, access it, download results
cat ~/Downloads/assignments_from_pool_962392__20-08-2021.tsv | cut -f 1,8 | grep -v 'INPUT:sha256' | sort  >a
cat ~/smart_parser/tools/disclosures_site/predict_office/pools/pool????.txt  | sort   join -t $'\t' - a -o '1.1,1.2,2.2,1.4' >p.txt
cp p.txt ~/smart_parser/tools/disclosures_site/predict_office/pools/pool200a.txt


#on dev machine
cd $FOLDER
python3 ~/smart_parser/tools/disclosures_site/manage.py build_office_index --settings disclosures.settings.dev
python3 ~/smart_parser/tools/disclosures_site/predict_office/management/commands/prepare_train_pool.py --pool ~/smart_parser/tools/disclosures_site/predict_office/pools/train.declarator.txt  ~/smart_parser/tools/disclosures_site/predict_office/pools/train.sud.txt  ~/smart_parser/tools/disclosures_site/predict_office/pools/train.toloka.txt,3  --output-train-pool train_pool.txt
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_train --model-folder model  --train-pool train_pool.txt --epoch-count  19
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_test --test-pool ~/smart_parser/tools/disclosures_site/predict_office/pools/test.txt  --bigrams-path office_ngrams.txt  --model-folder model --threshold 0.99

