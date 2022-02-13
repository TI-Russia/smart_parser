import os.path
import sys
import argparse

TOOLS_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(TOOLS_FOLDER)

from common.logging_wrapper import setup_logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mysql-version", dest='mysql_version')
    parser.add_argument("--elasticsearch-version", dest='elasticsearch_version')
    return parser.parse_args()


class TUpdater:
    def __init__(self):
        self.logger = setup_logging("source_updater")
        self.args = parse_args()

    def run_cmd(self, cmd):
        self.logger.info(cmd)
        exit_value = os.system(cmd)
        if exit_value != 0:
            raise Exception("{} failed".format(cmd))

    def check_version(self, service, expected_version):
        self.run_cmd('sudo {} --version > /tmp/version'.format(service))
        with open('/tmp/version') as inp:
            v = inp.read()
            if v.strip() != expected_version.strip():
                diff = ""
                for index, (i1,i2) in  enumerate(zip(v, expected_version)):
                    if i1 != i2:
                        diff = v[index:]
                raise Exception("Service {}, backend version = {}, prod version = {}, diff starts with {}".format(service, expected_version, v, diff))

    def main(self):
        disclosures_folder = os.path.join(os.path.dirname(__file__), "..")
        os.chdir(disclosures_folder)

        self.run_cmd('sudo ls >/dev/null')          #check sudo without password
        self.check_version('mysqld', self.args.mysql_version)
        self.check_version('/usr/share/elasticsearch/bin/elasticsearch', self.args.elasticsearch_version)
        self.run_cmd('git log -n 1 .. >> last_commits.txt')
        self.run_cmd('git pull')
        self.run_cmd('{} -m pip install -r ../requirements.txt'.format(sys.executable))
        self.run_cmd('PYTHONPATH={} {} manage.py test --tag=front --settings disclosures.settings.dev declarations/tests  --no-input'.format(
            TOOLS_FOLDER, sys.executable
        ))

        self.logger.info("all done")


if __name__ == '__main__':
    TUpdater().main()
