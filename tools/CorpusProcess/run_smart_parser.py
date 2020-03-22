#!/usr/bin/env python
import re
import sys
import os
import tqdm
from datetime import datetime
import requests
import json
import logging
from requests.auth import HTTPBasicAuth
from setuptools import glob
from multiprocessing import Pool
import signal
import argparse

SMART_PARSER = '..\\..\\src\\bin\\Debug\\netcoreapp3.1\\smart_parser.exe'
declarator_domain = 'https://declarator.org'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-count", dest='parallel_pool_size', help="run smart parser in N parallel processes",
                        default=4, type=int)
    parser.add_argument("--limit", dest='limit', help="Run smart parser only for N tasks",
                        default=None, type=int)
    parser.add_argument("--use-cache", dest='usecache', help="Parse only new files, skip existing JSONs",
                        default=False, type=bool)
    parser.add_argument("--output", dest='output', help="Output and cache folder to store results.",
                        default="out", type=str)
    parser.add_argument("--force-upload", dest='force_upload',
                        help="Output and cache folder to store results.",
                        default=False, type=bool, action="store_true")
    parser.add_argument("--joblist", dest='joblist', help="API URL with joblist or folder with files",
                        default="https://declarator.org/api/fixed_document_file/?office=579", type=str)
    parser.add_argument("-e", dest='extensions', default=['doc', 'docx', 'pdf', 'xls', 'xlsx', 'htm', 'html', 'rtf'],
                        action='append',
                        help="extensions: doc, docx, pdf, xsl, xslx, take all extensions if  this argument is absent")
    return parser.parse_args()


def check_extension(filename, all_extension):
    if all_extension is None:
        return True
    for x in all_extension:
        if filename.endswith(x):
            return True
    return False


# Create a custom logger
def get_logger():
    logger = logging.getLogger(__name__)

    # Create handlers
    f_handler = logging.FileHandler('parsing.log', 'w', 'utf-8')
    f_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # Create formatter and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)

    # # Add handlers to the logger
    # logger.addHandler(f_handler)
    return logger


logger = get_logger()

client = requests.Session()
credentials = json.load(open('auth.json'))
client.auth = HTTPBasicAuth(credentials['username'], credentials['password'])


def download_file(file_url, filename):
    if os.path.isfile(file_url):
        return file_url
    path, _ = os.path.split(filename)
    os.makedirs(path, exist_ok=True)
    result = requests.get(file_url)
    filename = re.sub(r"[<>?:|]", "", filename)
    with open(filename, 'wb') as fd:
        fd.write(result.content)

    return filename


def run_smart_parser(filepath, args):
    """start SmartParser for one file"""
    start_time = datetime.now()
    sourcefile = filepath[:filepath.rfind('.')]

    json_list = glob.glob("%s*.json" % sourcefile)
    if json_list:
        if not args.usecache:
            logger.info("Delete existed JSON file(s).")
            for jf in json_list:
                os.remove(jf)
        else:
            logger.info("Skipping existed JSON file %s.json" % sourcefile)
            return

    if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        smart_parser_options = r"-adapter aspose -license C:\smart_parser\src\bin\Release\lic.bin"
    else:
        smart_parser_options = "-adapter prod -converted-storage-url http://declarator.zapto.org:8000/converted_document"

    log = filepath + ".log"
    if os.path.exists(log):
        os.remove(log)

    cmd = "{} {} \"{}\"".format(
        SMART_PARSER,
        smart_parser_options,
        filepath)
    result = os.popen(cmd).read()
    return (datetime.now() - start_time).total_seconds()


def post_results(sourcefile, job, time_delta=None, ):
    df_id, archive_file = job.get('document_file', None), job.get('archive_file', None)
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
                file_year = file_data.get('document', {}).get('year')

                expected_year = job.get('income_year', None)
                if file_year is not None and expected_year is not None and file_year != expected_year:
                    logger.warning("Skip wrong declaration year %i (expected %i)" % (
                        file_year, expected_year))
                    continue
                data['persons'] += file_data['persons']
                if data['document']:
                    if data['document'].get('sheet_title') != file_data['document'].get('sheet_title'):
                        logger.warning(
                            "Document sheet title changed in one XLSX!")
                data['document'] = file_data['document']

    if 'sheet_number' in data['document']:
        del data['document']['sheet_number']

    data['document']['file_size'] = os.path.getsize(sourcefile)
    try:
        data['document']['parser_log'] = open(
            sourcefile + ".log", 'rb').read().decode('utf-8', errors='ignore')
    except FileNotFoundError:
        data['document']['parser_log'] = "FileNotFoundError: " + \
                                         sourcefile + ".log"

    data['document']['documentfile_id'] = df_id
    if archive_file:
        data['document']['archive_file'] = archive_file

    # if time_delta == PARSER_TIMEOUT:
    #     data['document']['parser_log'] += "\nTimeout %i exceeded for smart_parser.exe" % PARSER_TIMEOUT

    if time_delta:
        data['document']['parser_time'] = time_delta

        body = json.dumps(data, ensure_ascii=False, indent=4).encode(
            'utf-8', errors='ignore')

        with open(filename + ".json", "wb") as fp:
            fp.write(body)
    
    parsed = len(data['persons']) > 0

    if df_id:
        if job['status'] == 'ok' and not parsed:
            return 'degrade'
                    
        logger.info("POSTing results (id=%i): %i persons, %i files, file_size %i" % (
            df_id, len(data['persons']), len(json_list), data['document']['file_size']))

        response = client.post(declarator_domain +
                               '/api/jsonfile/validate/', data=body)
        if response.status_code != requests.codes.ok:
            logger.error(response)
            logger.error(response.text)

    if not parsed:
        return 'error'

    return 'ok'


def kill_process_windows(pid):
    os.system("taskkill /F /T /PID " + str(pid))


class ProcessOneFile(object):
    def __init__(self, args, parent_pid):
        self.args = args
        self.parent_pid = parent_pid

    def __call__(self, job):
        try:
            return self.run_job(job)

        except KeyboardInterrupt:
            kill_process_windows(self.parent_pid)

    def run_job(self, job):
        file_url, df_id, archive_file = (
            job.get('download_url', None),
            job.get('document_file', None),
            job.get('archive_file', None))
        logger.info("Running job (id=%s) with URL: %s" % (df_id, file_url))

        url_path, filename = os.path.split(file_url)
        filename, ext = os.path.splitext(filename)

        if archive_file:
            file_path = os.path.join(
                self.args.output, str(df_id), archive_file)
        elif not df_id:
            file_path = file_url
        else:
            file_path = os.path.join(self.args.output, "%i%s" % (df_id, ext))

        file_path = download_file(file_url, file_path)

        time_delta = run_smart_parser(file_path, self.args)

        if time_delta is not None:
            return post_results(file_path, job, time_delta)
        else:
            # this is wrong for header_recall calculation:
            # time_delta 0 for cached parsing results
            logger.error("time_delta=None for %s" % file_path)
            return False


def download_jobs(url=None, stop=False):
    """API call return list of files to parse (paged now)"""

    next_url = url
    while next_url:
        logger.info("GET Joblist URL: %s" % next_url)
        result = json.loads(client.get(next_url).content.decode('utf-8'))
        next_url = result['next']
        if stop:
            next_url = None
        file_list = result['results']
        for obj in file_list:
            yield obj


def get_folder_jobs(folder, args):
    """Generate job list from folder with files"""
    filenames = os.listdir(folder)
    joblist = []
    for name in filenames:
        if not check_extension(name, args.extensions):
            continue
        joblist.append({
            "download_url": os.path.join(folder, name),
        })
    return joblist


if __name__ == '__main__':
    args = parse_args()

    pool = Pool(args.parallel_pool_size)
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, original_sigint_handler)

    joblist = args.joblist
    # joblist = "https://declarator.org/api/fixed_document_file/?queue=empty&filetype=html"

    try:
        if joblist.startswith('http'):
            joblist = list(download_jobs(joblist, stop=False))
        else:
            joblist = get_folder_jobs(joblist, args)
            if args.limit:
                joblist = joblist[:args.limit]

        logger.info("Starting %i jobs" % len(joblist))

        results = list(pool.imap(ProcessOneFile(
            args, os.getpid()), joblist, chunksize=1))
    except KeyboardInterrupt:
        print("stop processing...")
        pool.terminate()
    else:
        pool.close()

    total = len(results)
    ok = len(list(filter(lambda x: x == 'ok', results)))
    degrade = len(list(filter(lambda x: x == 'degrade', results)))

    print("Total files: %i" % (total))
    print("Succeed files: %i" % (ok))
    print("Errors: %i" % (total - ok))
    print("Degraded: %i" % (degrade))

    print("Header_recall: %f" %
          ((total - ok) / float(total)))
