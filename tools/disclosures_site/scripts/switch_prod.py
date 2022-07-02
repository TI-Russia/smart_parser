import argparse
import os.path
import shutil
import sys

TOOLS_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(TOOLS_FOLDER)


from common.logging_wrapper import setup_logging
from elasticsearch import Elasticsearch


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mysql-tar", dest='mysql_tar', default=None)
    parser.add_argument("--elasticsearch-tar", dest='elasticsearch_tar', default=None)
    parser.add_argument("--sitemap-tar", dest='sitemap_tar', default=None)
    parser.add_argument("--misspell-folder", dest='misspell_folder', default=None)
    parser.add_argument("--host", dest='host', default="disclosures.ru")
    return parser.parse_args()


class TSwitcher:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("switch_prod")

    def run_cmd(self, cmd):
        self.logger.info(cmd)
        exit_value = os.system(cmd)
        if exit_value != 0:
            raise Exception("{} failed".format(cmd))

    def switch_service(self, service, prod_folder, new_folder, backup_folder):
        self.run_cmd("sudo systemctl stop {}".format(service))
        self.run_cmd("sudo mv {} {}".format(prod_folder, backup_folder))
        self.run_cmd("sudo mv {} {}".format(new_folder, prod_folder))
        self.run_cmd("sudo systemctl start {}".format(service))
        self.run_cmd("sudo systemctl status {} ".format(service))

    def check_mysql(self):
        sql_check = '{} manage.py external_link_surname_checker --links-input-file data/external_links.json  --settings disclosures.settings.prod'.format(
            sys.executable
        )
        self.run_cmd(sql_check)

    def check_elasticsearch(self):
        es = Elasticsearch()
        indices = ['declaration_person_prod', 'declaration_sections_prod', 'declaration_office_prod', 'declaration_file_prod']
        for index_name in indices:
            es.indices.refresh(index_name)
            cnt = es.cat.count(index_name, params={"format": "json"})
            if int(cnt[0]['count']) < 10000:
                raise Exception("the index {} is too small".format(index_name))
        query_body = {
            "query": {
                "bool": {
                    "must": {
                        "match": {
                            "id": 1409527
                        }
                    }
                }
            }
        }
        res = es.search(body=query_body, index="declaration_person_prod", )
        hits = res['hits']['hits']
        if len(hits) != 1 or hits[0]["_source"]["person_name"] != "Путин Владимир Владимирович":
            raise Exception("cannot find a Putin or there are to many Putins in the db")

    def switch_service_or_rollback(self, service, tar_path, check_func):
        new_folder =  '/var/lib/{}.new'.format(service)
        backup_folder = '/var/lib/{}.old'.format(service)
        prod_folder = '/var/lib/{}'.format(service)
        self.run_cmd('sudo rm -rf {}'.format(new_folder))
        self.run_cmd('sudo rm -rf {}'.format(backup_folder))
        self.run_cmd('sudo -n mkdir {}'.format(new_folder))
        self.run_cmd('sudo chmod a+rxw {}'.format(new_folder))
        self.run_cmd('sudo chown {} {}'.format(service, new_folder))
        self.run_cmd('sudo tar --file {} --gzip --directory {} --extract'.format(tar_path, new_folder))
        try:
            self.switch_service(service, prod_folder, new_folder,  backup_folder)
            check_func()
        except Exception as exp:
            self.logger.info("rollback {}".format(service))
            self.switch_service(service, prod_folder, backup_folder, new_folder)
            raise

    def switch_misspell(self, new_folder):
        backup = "data/misspell_bin.sav"
        prod ="data/misspell_bin"
        if os.path.exists(backup):
            shutil.rmtree(backup)
        shutil.move(prod, backup)
        shutil.move(new_folder, prod)

    def test_final(self):
        cmd = 'PYTHONPATH={} {} scripts/dolbilo.py --input-requests data/dolbilo_requests.txt --host {}'.format(
            TOOLS_FOLDER, sys.executable, self.args.host
        )
        self.run_cmd(cmd)

    def main(self):
        #check sudo without password
        self.run_cmd('sudo ls >/dev/null')

        disclosures_folder = os.path.join(os.path.dirname(__file__), "..")
        os.chdir(disclosures_folder)
        if self.args.mysql_tar is not None:
            self.switch_service_or_rollback('mysql', self.args.mysql_tar, self.check_mysql)
        else:
            self.logger.info("skip mysql updating")
        if self.args.elasticsearch_tar is not None:
            self.switch_service_or_rollback('elasticsearch', self.args.elasticsearch_tar, self.check_elasticsearch)
        else:
            self.logger.info("skip elasticsearch updating")

        try:
            if self.args.sitemap_tar is not None:
                self.run_cmd('tar xf {}'.format(self.args.sitemap_tar))
            else:
                self.logger.info("skip sitemap updating")
            if self.args.misspell_folder is not None:
                self.switch_misspell(self.args.misspell_folder)
            else:
                self.logger.info("skip misspell updating")

            self.run_cmd('sudo systemctl restart gunicorn')
            self.test_final()
        except Exception as exp:
            self.logger.error("mysql and elasticsearch are new (not rollbacked), but we cannot proceed due {}".format(exp))
            raise

        self.logger.info("all done")


if __name__ == '__main__':
    TSwitcher().main()
