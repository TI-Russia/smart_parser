#!/usr/bin/env python
import re
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

job_list_file = 'parser-job-htm-errors.json'
smart_parser = '..\\..\\src\\bin\\Release\\netcoreapp3.1\\smart_parser.exe'
declarator_domain = 'https://declarator.org'

client = requests.Session()
credentials = json.load(open('auth.json'))
client.auth = HTTPBasicAuth(credentials['username'], credentials['password'])

# PARSER_TIMEOUT = 600


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-count", dest='parallel_pool_size', help="run smart parser in N parallel processes",
                        default=4, type=int)
    parser.add_argument("--limit", dest='limit', help="Run smart parser only for N tasks",
                        default=None, type=int)
    parser.add_argument("--restart", dest='restart', help="Parse all files, ignore existing JSONs",
                        default=False, type=bool)
    return parser.parse_args()


def download_file(file_url, filename):
    if os.path.isfile(filename):
        return filename
    path, _ = os.path.split(filename)
    os.makedirs(path, exist_ok=True)
    result = requests.get(file_url)
    filename = re.sub(r"[<>?:|]", "", filename)
    with open(filename, 'wb') as fd:
        fd.write(result.content)

    return filename


def get_parsing_list(filename, url=None):
    """download and cache list of files to parse"""

    if not os.path.isfile(filename):
        if not url:
            url = declarator_domain + '/media/metrics/%s' % filename
        result = client.get(url)
        with open(filename, "wb") as fp:
            fp.write(result.content)

    file_list = json.load(open(filename, 'r', encoding='utf8'))

    logger.info("%i jobs listed" % len(file_list))
    return file_list


def run_smart_parser(filepath, args):
    """start SmartParser for one file"""
    start_time = datetime.now()
    sourcefile = filepath[:filepath.rfind('.')]

    json_list = glob.glob("%s*.json" % sourcefile)
    if json_list:
        if args.restart:
            logger.info("Delete existed JSON file(s).")
            for jf in json_list:
                os.remove(jf)
        else:
            return

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

    json_list = glob.glob("%s.json" % filename)
    if len(json_list) == 1:
        # Properly constructed final JSON found
        data = json.load(open(json_list[0], encoding='utf8'))
    else:
        json_list = glob.glob("%s*.json" % filename)
        if not json_list:
            # Build empty JSON to post report in API and skip parsing attemp in a future
            data = {'document': {'documentfile_id': df_id}, 'persons': []}
            if archive_file:
                data['document']['archive_file'] = archive_file
        else:
            # Join separated JSON files (of XLSX lists)
            json_list = glob.glob("%s*.json" % filename)
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

    # if time_delta == PARSER_TIMEOUT:
    #     data['document']['parser_log'] += "\nTimeout %i exceeded for smart_parser.exe" % PARSER_TIMEOUT

    if time_delta:
        data['document']['parser_time'] = time_delta

    logger.info("POSTing results (id=%i): %i persons, %i files, file_size %i" % (
        df_id, len(data['persons']), len(json_list), data['document']['file_size']))
    
    body = json.dumps(data, ensure_ascii=False, indent=4).encode('utf-8', errors='ignore')
    
    with open(filename + ".json", "wb") as fp:
        fp.write(body)

    response = client.post(declarator_domain + '/api/jsonfile/validate/', data=body)
    if response.status_code != requests.codes.ok:
        logger.error(response)
        logger.error(response.text)


def kill_process_windows(pid):
    os.system("taskkill /F /T /PID " + str(pid))


class ProcessOneFile(object):
    def __init__(self, args, parent_pid):
        self.args = args
        self.parent_pid = parent_pid

    def __call__(self, job):
        try:
            # ZIP-Archives parse in one process file by file
            if job['file'].endswith('.zip'):
                for sub_job in job['archive_files']:
                    if sub_job.endswith('.pdf'):
                        continue
                    url = "/office/view-zip-file/%i/%s" % (job['id'], sub_job)
                    self.run_job(url, job['id'], sub_job)
            elif job['file'].endswith('.pdf'):
                pass
            else:
                self.run_job(job['file'], job['id'])
        except KeyboardInterrupt:
           kill_process_windows(self.parent_pid)

    def run_job(self, file_url, df_id, archive_file=None):
        logger.info("Running job (id=%i) with URL: %s" % (df_id, file_url))
        url_path, filename = os.path.split(file_url)
        filename, ext = os.path.splitext(filename)

        if archive_file:
            file_path = os.path.join("out", str(df_id), "%s%s" % (filename, ext))
        else:
            file_path = os.path.join("out", "%i%s" % (df_id, ext))

        file_path = download_file(declarator_domain + file_url, file_path)
        time_delta = run_smart_parser(file_path, self.args)
        if time_delta:
            post_results(file_path, df_id, archive_file, time_delta)


if __name__ == '__main__':
    args = parse_args()

    pool = Pool(args.parallel_pool_size)
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, original_sigint_handler)

    try:
        job_list = get_parsing_list(job_list_file, "https://declarator.org/api/document_file/parsing_list/?error=Unknown%20file%20extension%20.htm")
        res = pool.map(ProcessOneFile(args, os.getpid()), job_list)
    except KeyboardInterrupt:
        print("stop processing...")
        pool.terminate()
    else:
        pool.close()
