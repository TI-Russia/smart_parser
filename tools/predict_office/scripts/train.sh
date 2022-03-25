FOLDER=~/tmp/predict_office/tf.00
mkdir -p $FOLDER

# go to central server(migalka)
# create train and test from declarator data
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action build_office_train_set  --input-file dlrobot_human.dbm --predict-office-pool  office_declarator_pool.txt
scp office_declarator_pool.txt dev_machine:$FOLDER

# refresh test and train pools on migalka, then copy it to developer notebook
cd ~/smart_parser/tools/disclosures_site/predict_office/pools
for src in `ls *.source.txt`; do
  output_file=${src%.source.txt}.txt
  echo "$src -> $output_file"
  python3 ~/smart_parser/tools/dlrobot_human/scripts/dlrobot_human_manager.py \
    --action rebuild_ml_pool \
    --input-file  ~/declarator_hdd/declarator/dlrobot_updates/1629223992/dlrobot_human.dbm \
    --input-predict-office-pool $src  \
    --output-predict-office-pool $output_file
done

# create a pool for toloka
#take 200 cases that was predicted by ML
cat cases_to_predict_dump.txt  | grep -v 'service.nalog.ru' | grep -v '{" title": "", "roles": [], "departments": []' | head -n 200 |  sort >pool.mos.ru.txt
#take their sha256's
cut -f 1  pool.mos.ru.txt >a.1
#get predicted office_id and print it to pool
python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action to_json  --sha256-list-file a.1 --input-file dlrobot_human.dbm | jq -rc '.documents | to_entries[] | [.key, .value.office_id] | @tsv' | sort >a.sha_office
join -t $'\t' pool.mos.ru.txt  a.sha_office  | awk -F "\t" -v  OFS="\t" '{print $1,$2,$5,$4}' >pool.mos.ru.txt.with_office_id
python3 ~/smart_parser/tools/predict_office/scripts/tf_office_toloka.py --model-folder model --test-pool pool200a.txt --toloka-output-pool toloka.txt

# go to toloka, add a new pool, access it, download results
# https://sandbox.toloka.yandex.ru/requester/project/74069

cat ~/Downloads/assignments_from_pool_962392__20-08-2021.tsv | cut -f 1,8 | grep -v 'INPUT:sha256' | sort  >a
cat ~/smart_parser/tools/predict_office/pools/pool????.txt  | sort   join -t $'\t' - a -o '1.1,1.2,2.2,1.4' >p.txt
cp p.txt ~/smart_parser/tools/predict_office/pools/pool200a.txt


#on dev machine
cd $FOLDER

# If you loose train.declarator.txt, then you can restore it by pools/train.declarator.source.txt (in git)
# In principle, train.declarator.txt contains all declarator markup (document, office) pairs,
# so train.declarator.txt cam be rebuilt by command
# python /home/sokirko/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action build_office_train_set
# I remember that train.declarator.txt was somehow modified after creation (I forgot the details).

python3 ~/smart_parser/tools/predict_office/scripts/build_office_index.py
python3 ~/smart_parser/tools/predict_office/scripts/prepare_train_pool.py --pool ~/tmp/predict_office/train.declarator.txt  ~/smart_parser/tools/predict_office/pools/train.sud.txt  ~/smart_parser/tools/predict_office/pools/train.toloka.txt,3  --output-train-pool train_pool.txt
python3 ~/smart_parser/tools/predict_office/scripts/tf_office_train.py --model-folder model  --train-pool train_pool.txt --epoch-count  19
python3 ~/smart_parser/tools/predict_office/scripts/tf_office_test.py --test-pool ~/smart_parser/tools/predict_office/pools/test_fixed.txt  --bigrams-path office_ngrams.txt  --model-folder model --threshold 0.99


=============
new sites
#python3 ~/smart_parser/tools/disclosures_site/scripts/dlrobot_human.py --action unknown_office_uniq_website_pool --input-file ~/declarator_hdd/declarator/dlrobot_updates/1644319081/dlrobot_human.dbm --output-predict-office-pool new_sites_pool.tx
#python3 ~/smart_parser/tools/disclosures_site/scripts/predict_office/manage_pool.py --input-pool new_sites_pool.txt  --output-toloka-file toloka.txt --output-automatic-file automatic.txt
===
python3 ~/smart_parser/tools/dlrobot_human/scripts/dlrobot_human_manager.py --action weak_offices --input-file ~/declarator_hdd/declarator/dlrobot_updates/1644319081/dlrobot_human.dbm --output-predict-office-pool weak_offices_pool.txt
python3 ~/smart_parser/tools/predict_office/scripts/manage_pool.py --input-pool weak_offices_pool.txt  --output-toloka-file toloka.txt --output-automatic-file weak_automatic.txt

==
datasphere
cd ~/tmp/predict_office/tf41
scp office_ngrams.txt ~/smart_parser/tools/predict_office/pools/test_fixed.txt train_pool.txt iphil:/data/sokirko/predict_office