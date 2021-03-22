MYSQL_TAR=$1
ELASTICSEARCH_TAR=$2
STATIC_SECTIONS=$3
HOST=${4:"disclosures.ru"}
SERVICE_USER=sokirko
DISCLOSURES_FOlDER=/home/$SERVICE_USER/smart_parser/tools/disclosures_site
cd $DISCLOSURES_FOlDER

function switch_service() {
  local service=$1
  local prod=$2
  local new=$3
  local backup=$4
  sudo systemctl stop $service
  sudo mv $prod $backup
  sudo mv $new $prod
  sudo systemctl start $service
}

#1. mysql
NEW_MYSQL=/var/lib/mysql.new
BACKUP_MYSQL=/var/lib/mysql.old
PROD_MYSQL=/var/lib/mysql

#1.1 unpack
if [ -d $NEW_MYSQL ]; then sudo rm -rf $NEW_MYSQL; fi
sudo mkdir $NEW_MYSQL
sudo chmod a+rxw $NEW_MYSQL
sudo chown mysql $NEW_MYSQL
sudo tar --file $MYSQL_TAR --gzip --directory $NEW_MYSQL --extract

#1.2 switching
sudo rm -rf $BACKUP_MYSQL
switch_service mysql $PROD_MYSQL $NEW_MYSQL $BACKUP_MYSQL

#1.3 test
sudo -u $SERVICE_USER bash -c -l '
  python3 manage.py external_link_surname_checker --links-input-file data/external_links.json  --settings disclosures.settings.prod
'
if [ $? != 0 ]; then
    echo "external_link_surname_checker failed, roll back"
    switch_service mysql $PROD_MYSQL $BACKUP_MYSQL $NEW_MYSQL
    exit 1
fi

#2.  elastic search
NEW_ES=/var/lib/elasticsearch.new
BACKUP_ES=/var/lib/elasticsearch.old
PROD_ES=/var/lib/elasticsearch

if [ -d $NEW_ES ]; then sudo rm -rf $NEW_ES; fi
sudo mkdir $NEW_ES
sudo chmod a+rxw $NEW_ES
sudo chown elasticsearch $NEW_ES
sudo tar --file $ELASTICSEARCH_TAR --gzip --directory $NEW_ES --extract
sudo rm -rf $BACKUP_ES

switch_service elasticsearch $PROD_ES $NEW_ES $BACKUP_ES

sleep 10
putin=`curl -s localhost:9200/declaration_person_prod/_search -H 'Content-Type: application/json' -d '{ "query": { "term": {"id": 1409527}}}' | jq -r '.hits["hits"][0]["_source"]["person_name"]'`
if [ "$putin" != "Путин Владимир Владимирович" ]; then
    echo "Fatal error! Cannot find a person in elasticsearch, roll back"
    switch_service elasticsearch $PROD_ES $BACKUP_ES $NEW_ES
    exit 1
fi

#3.  sitemaps
tar --file $STATIC_SECTIONS --gzip --directory disclosures/static --extract ;
python3 manage.py generate_sitemaps --settings disclosures.settings.prod --output-file disclosures/static/sitemap.xml

#4  restart
sudo systemctl restart gunicorn

#5 testing
req_count=`python3 scripts/dolbilo.py --input-access-log data/access.test.log.gz  --host $HOST | jq ".normal_response_count"`

if [ "$req_count" != "349" ]; then
  echo "site testing returns only $req_count requests with 200 http code, must be 349"
  exit 1
fi

echo "all done"
