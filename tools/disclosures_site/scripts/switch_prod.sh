#run this script as a root

MYSQL_TAR=$1
ELASTICSEARCH_TAR=$2
STATIC_SECTIONS=$3
SERVICE_USER=sokirko
DISCLOSURES_FOlDER=/home/$SERVICE_USER/smart_parser/tools/disclosures_site
cd $DISCLOSURES_FOlDER


#1. mysql
NEW_MYSQL=/var/lib/mysql.new
BACKUP_MYSQL=/var/lib/mysql.old
PROD_MYSQL=/var/lib/mysql

#1.1 unpack
if [ -d $NEW_MYSQL ]; then rm -rf $NEW_MYSQL; fi
mkdir $NEW_MYSQL
chmod a+rxw $NEW_MYSQL
chown mysql $NEW_MYSQL
tar --file $MYSQL_TAR --gzip --directory $NEW_MYSQL --extract

rm -rf $BACKUP_MYSQL

#1.2 switching
systemctl stop mysql
mv $PROD_MYSQL $BACKUP_MYSQL
mv $NEW_MYSQL $PROD_MYSQL
systemctl start mysql

#1.3 test
sudo -u $SERVICE_USER bash -c -l '
  python3 manage.py external_link_surname_checker --links-input-file data/external_links.json  --settings disclosures.settings.prod
'
if [ $? != 0 ]; then
    echo "external_link_surname_checker failed, roll back"
    systemctl stop mysql
    mv $PROD_MYSQL $NEW_MYSQL
    mv $BACKUP_MYSQL $PROD_MYSQL
    systemctl start mysql
    exit 1
fi

#2.  elastic search
NEW_ES=/var/lib/elasticsearch.new
BACKUP_ES=/var/lib/elasticsearch.old
PROD_ES=/var/lib/elasticsearch

if [ -d $NEW_ES ]; then rm -rf $NEW_ES; fi
mkdir $NEW_ES
chmod a+rxw $NEW_ES
chown elasticsearch $NEW_ES
tar --file $ELASTICSEARCH_TAR --gzip --directory $NEW_ES --extract
rm -rf $BACKUP_ES

systemctl stop elasticsearch
mv $PROD_ES $BACKUP_ES
mv $NEW_ES $PROD_ES
systemctl start elasticsearch
sleep 10
putin=`curl -s localhost:9200/declaration_person_prod/_search -H 'Content-Type: application/json' -d '{ "query": { "term": {"id": 1409527}}}' | jq -r '.hits["hits"][0]["_source"]["person_name"]'`
if [ "$putin" != "Путин Владимир Владимирович" ]; then
    echo "Fatal error! Cannot find a person in elasticsearch, roll back"
    systemctl stop elasticsearch
    mv $PROD_ES $NEW_ES
    mv $BACKUP_ES $PROD_ES
    systemctl start elasticsearch
    exit 1
fi

#3.  sitemaps
sudo -u $SERVICE_USER bash -c -l -x "
  tar --file $STATIC_SECTIONS --gzip --directory disclosures/static --extract ;
  python3 manage.py generate_sitemaps --settings disclosures.settings.prod --output-file disclosures/static/sitemap.xml
"

#4  restart
systemctl restart gunicorn

#5 testing
sudo -u $SERVICE_USER bash -c -l -x '
req_count=`python3 scripts/dolbilo.py --input-access-log data/access.test.log.gz  --host disclosures.ru| jq ".normal_response_count"`

if [ "$req_count" != "349" ]; then
  echo "site testing returns only $req_count requests with 200 http code, must be 349"
  exit 1
fi
'
if [ $? != 0 ]; then
  exit 1
fi
echo "all done"
