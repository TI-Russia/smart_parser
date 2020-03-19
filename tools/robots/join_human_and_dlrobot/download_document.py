import requests
import json
import logging
from requests.auth import HTTPBasicAuth
import os
import sys
import argparse

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(0)
# job_list_file = 'parser-job-priority-2.json'
job_list_file = "media/metrics/parser-job-list.json"
declarator_domain = 'https://declarator.org'

client = requests.Session()
credentials = json.load(open('auth.json'))
client.auth = HTTPBasicAuth(credentials['username'], credentials['password'])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document-id",
        dest='document_id')
    parser.add_argument(
        "--extension",
        dest='extension')
    return parser.parse_args()


def download_file(file_url, filename):
    if os.path.isfile(filename):
        return
    path, _ = os.path.split(filename)
    os.makedirs(path, exist_ok=True)
    print("download {0}  to {1}".format(file_url, filename))
    result = requests.get(file_url)
    with open(filename, 'wb') as fd:
        fd.write(result.content)


def get_parsing_list():
    cachefilename = "parser-job-list.json"
    if not os.path.isfile(cachefilename):
        url = os.path.join(declarator_domain, "media/metrics/parser-job-list.json");
        print("download files from {0} to {1}...".format(url, cachefilename))
        result = client.get(url)
        with open(cachefilename, "w", encoding="utf8") as fp:
            file_list = json.loads(result.content)
            files = {}
            for i in file_list:
                files[i['id']] = i
            json.dump(files, fp)

    with open(cachefilename, "r", encoding="utf8") as fp:
        return json.load(fp)


def download_file_by_id(document_id):
    job = jobs[document_id]
    file_url = job['file']
    url_path, filename = os.path.split(file_url)
    filename, ext = os.path.splitext(filename)
    file_path = os.path.join("out", "%s%s" % (document_id, ext))
    download_file(declarator_domain + file_url, file_path)


if __name__ == '__main__':
    args = parse_args()
    jobs = get_parsing_list()
    if args.extension is not None:
        for file_id, fileinfo in jobs.items():
            if fileinfo['file'].lower().endswith("pdf"):
                sys.stderr.write("download {}\n".format(fileinfo['file']))
                download_file_by_id(file_id)
    else:
        download_file_by_id(args.document_id)
