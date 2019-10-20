#!/usr/bin/env python
import sys
import os
from datetime import datetime
import requests
import json
import logging
from requests.auth import HTTPBasicAuth
from setuptools import glob
from multiprocessing import Pool
import signal
import argparse

# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers
f_handler = logging.FileHandler('parsing.log', 'w', 'utf-8')
f_handler.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Create formatter and add it to handlers
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)

job_list_file = 'parser-job-priority-1.json'
smart_parser = '..\\..\\src\\bin\\Release\\smart_parser.exe'
declarator_domain = 'https://declarator.org'

client = requests.Session()
credentials = json.load(open('auth.json'))
client.auth = HTTPBasicAuth(credentials['username'], credentials['password'])


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-count", dest='parallel_pool_size', help="run smart parser in N parallel processes",
                        default=4, type=int)
    return parser.parse_args()


def download_file(file_url, filename):
    if os.path.isfile(filename):
        return
    path, _ = os.path.split(filename)
    os.makedirs(path, exist_ok=True)
    result = requests.get(file_url)
    with open(filename, 'wb') as fd:
        fd.write(result.content)


def get_parsing_list(filename):
    """get list of files to parse"""

    if not os.path.isfile(filename):
        result = client.get(declarator_domain + '/media/dumps/%s' % filename)
        with open(filename, "wb") as fp:
            fp.write(result.content)

    file_list = json.load(open(filename))

    logger.info("%i files listed" % len(file_list))
    return file_list


def run_smart_parser(filepath):
    """start SmartParser for one file"""
    start_time = datetime.now()
    sourcefile = filepath[:filepath.rfind('.')]

    json_list = glob.glob("%s*.json" % sourcefile)
    if json_list:
        logger.info("Delete existed JSON file(s).")
        for jf in json_list:
            os.remove(jf)

    if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        smart_parser_options = "-adapter aspose -license \"http://95.165.168.93:8088/lic.bin\""
    else:
        smart_parser_options = "-adapter prod"

    log = filepath + ".log"
    if os.path.exists(log):
        os.remove(log)

    cmd = "{} {} \"{}\"".format(
        smart_parser,
        smart_parser_options,
        filepath)
    os.system(cmd)
    return (datetime.now() - start_time).total_seconds()


def post_results(sourcefile, df_id, archive_file, time_delta=None):
    filename = sourcefile[:sourcefile.rfind('.')]
    json_list = glob.glob("%s*.json" % filename)

    if not json_list:
        data = {'document': {'documentfile_id': df_id}, 'persons': []}
        if archive_file:
            data['document']['archive_file'] = archive_file

    elif len(json_list) == 1:
        data = json.load(open(json_list[0], encoding='utf8'))

    else:
        data = {'persons': [], 'document': {}}
        for json_file in json_list:
            file_data = json.load(open(json_file, encoding='utf8'))
            data['persons'] += file_data['persons']
            if data['document']:
                if data['document'].get('sheet_title') != file_data['document'].get('sheet_title'):
                    logger.warning("Document sheet title changed in one XLSX!")
            data['document'] = file_data['document']

    if 'sheet_number' in data['document']:
        del data['document']['sheet_number']

    data['document']['file_size'] = os.path.getsize(sourcefile)
    try:
        data['document']['parser_log'] = open(sourcefile + ".log", 'rb').read().decode('utf-8', errors='ignore')
    except FileNotFoundError:
        data['document']['parser_log'] = "FileNotFoundError: " + sourcefile + ".log"

    if time_delta:
        data['document']['parser_time'] = time_delta

    logger.info("POSTing results: %i persons, %i files, file_size %i" % (
        len(data['persons']), len(json_list), data['document']['file_size']))
    body = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8', errors='ignore')
    response = client.post(declarator_domain + '/api/jsonfile/validate/', data=body)
    if response.status_code != requests.codes.ok:
        logger.error(response)
        logger.error(response.text)


def run_job(file_url, df_id, archive_file=None):
    logger.info("Running job (id=%i) with URL: %s" % (df_id, file_url))
    url_path, filename = os.path.split(file_url)
    filename, ext = os.path.splitext(filename)

    if archive_file:
        file_path = os.path.join("out", str(df_id), "%s%s" % (filename, ext))
    else:
        file_path = os.path.join("out", "%i%s" % (df_id, ext))

    download_file(declarator_domain + file_url, file_path)
    time_delta = run_smart_parser(file_path)
    post_results(file_path, df_id, archive_file, time_delta)


def kill_process_windows(pid):
    os.system("taskkill /F /T /PID " + str(pid))


class ProcessOneFile(object):
    def __init__(self, args, parent_pid):
        self.args = args
        self.parent_pid = parent_pid

    def __call__(self, job):
        try:
            # call smart parser
            run_job(job['file'], job['id'])
        except KeyboardInterrupt:
            kill_process_windows(self.parent_pid)


def do_job(job):
    if job['file'].endswith('.zip'):
        for sub_job in job['archive_files']:
            url = "/office/view-zip-file/%i/%s" % (job['id'], sub_job)
            run_job(url, job['id'], sub_job)
    else:
        run_job(job['file'], job['id'])


def job_iterator():
    jobs = get_parsing_list(job_list_file)
    for job in jobs[:4]:
        if job.get('done'):
            continue

        yield job

        # mark this job as done
        job['done'] = True
        with open(job_list_file, 'w') as fp:
            json.dump(jobs, fp, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    args = parse_args()

    pool = Pool(args.parallel_pool_size)
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = pool.map(ProcessOneFile(args, os.getpid()), job_iterator())
    except KeyboardInterrupt:
        print("stop processing...")
        pool.terminate()
    else:
        pool.close()
