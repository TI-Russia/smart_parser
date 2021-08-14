FOLDER=~/tmp/predict_office/tf.00
mkdir -p $FOLDER

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

#on dev machine
cd $FOLDER
manage=~/smart_parser/tools/disclosures_site/manage.py
python3 $manage office_index --settings disclosures.settings.prod
python3 $manage tensorflow_office --action split --all-pool office_declarator_pool.txt --train-pool train_pool.txt --test-pool test_pool.txt
python3 $manage tensorflow_office --action train --model-folder model  --train-pool train_pool.txt    --epoch-count  20
python3 $manage tensorflow_office --action test --model-folder model --test-pool test_pool.txt
python3 $manage tensorflow_office --action toloka --model-folder model --test-pool test_pool.txt --toloka-pool toloka.txt

