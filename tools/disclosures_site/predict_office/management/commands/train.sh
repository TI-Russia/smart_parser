FOLDER=~/tmp/predict_office/tf.00
mkdir -p $FOLDER

# create train and test from declarator data
#on migalka (where smart_parser_server is available)
echo "select d.sha256, f.web_domain, d.office_id from declarations_declarator_file_reference f join declarations_source_document d on d.id = f.source_document_id  into  outfile \"/tmp/docs.txt\"" | mysql -D disclosures_db -u disclosures -pdisclosures
sudo chmod a+rw "/tmp/docs.txt"
mkdir -p ~/tmp/docs_and_titles
cd ~/tmp/docs_and_titles
sudo mv "/tmp/docs.txt" .
cut -f 1  docs.txt >docs.txt.id
python3 ~/smart_parser/tools/smart_parser_http/smart_parser_client.py --action office_strings --sha256-list docs.txt.id > docs_office_strings.txt
paste docs.txt docs_office_strings.txt >office_declarator_pool.txt
scp office_declarator_pool.txt dev_machine:$FOLDER


# create a pool for toloka
cat dlrobot_human.json | jq -rc '.documents | to_entries[] | [.key, .value.office_id] | @tsv' | sort >a.new
shuf cases_to_predict_dump.txt  | grep -v 'service.nalog.ru' | grep -v '{"title": "", "roles": [], "departments": []' | head -n 200 |  sort | join -t $'\t' -  a.new  | awk -F "\t" -v  OFS="\t" '{print $1,$2,$5,$4}' >pool200.txt
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_toloka --model-folder model --test-pool pool200.txt --output-toloka-pool toloka.txt


#on dev machine
cd $FOLDER
python3 ~/smart_parser/tools/disclosures_site/manage.py office_index --settings disclosures.settings.prod
python3 ~/smart_parser/tools/disclosures_site/manage.py prepare_office_pool --declarator-pool ../office_declarator_pool.txt \
   --real-pool  ~/smart_parser/tools/disclosures_site/predict_office/pools/pool200.txt --real-pool-add-count  6 \
    --train-pool train_pool.txt
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_train --model-folder model  --train-pool train_pool.txt --epoch-count  20
python3 ~/smart_parser/tools/disclosures_site/manage.py tf_office_test --test-pool ~/smart_parser/tools/disclosures_site/predict_office/pools/pool100.txt  --bigrams-path office_ngrams.txt  --model-folder model --threshold 0.95

