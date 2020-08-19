#!/usr/bin/env python
import re
import sys
import os
import json
import logging
import tqdm
import signal
import argparse

import requests
from requests.packages.urllib3.util.retry import Retry
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter

from setuptools import glob
from multiprocessing import Pool
from datetime import datetime
from syslog import syslog

SMART_PARSER = '..\\..\\src\\bin\\Debug\\netcoreapp3.1\\smart_parser.exe'
if sys.platform in ['darwin', 'linux']:
    SMART_PARSER = 'dotnet ../../src/bin/Debug/netcoreapp3.1/smart_parser.dll'

declarator_domain = 'https://declarator.org'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-count", dest='parallel_pool_size', help="run smart parser in N parallel processes",
                        default=8, type=int)
    parser.add_argument("--limit", dest='limit', help="Run smart parser only for N tasks",
                        default=None, type=int)
    parser.add_argument("--use-cache", dest='usecache', help="Parse only new files, skip existing JSONs",
                        default=False, action="store_true")
    parser.add_argument("--output", dest='output', help="Output and cache folder to store results.",
                        default="out", type=str)
    parser.add_argument("--force-upload", dest='force_upload',
                        help="Force upload for degraded files.",
                        default=False, action="store_true")
    parser.add_argument("--download-only", dest='download_only',
                        help="Only download files to output folder, no pasring or anything else.",
                        default=False, action="store_true")
    parser.add_argument("--skip-upload", dest='skip_upload',
                        help="Skip upload for ALL files.",
                        default=False, action="store_true")
    parser.add_argument("--joblist", dest='joblist', help="API URL with joblist or folder with files",
                        default="https://declarator.org/api/fixed_document_file/?document_file=83450", type=str)
    parser.add_argument("-e", dest='extensions', default=['doc', 'docx', 'pdf', 'xls', 'xlsx', 'htm', 'html', 'rtf'],
                        action='append',
                        help="extensions: doc, docx, pdf, xsl, xslx, take all extensions if this argument is absent")
    return parser.parse_args()


def check_extension(filename, all_extension):
    if not all_extension:
        all_extension = ['doc', 'docx', 'pdf', 'xls', 'xlsx', 'htm', 'html', 'rtf']
    for x in all_extension:
        if filename.endswith(x):
            return True
    return False


# Create a custom logger
def get_logger():
    logger_obj = logging.getLogger(__name__)
    # logger.propagate = False

    # Create handlers
    f_handler = logging.FileHandler('parsing.log', 'w', 'utf-8')
    f_handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # Create formatter and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    f_handler.setFormatter(f_format)

    # # Add handlers to the logger
    logger_obj.addHandler(f_handler)
    return logger_obj


logger = get_logger()

retry_strategy = Retry(
    total=10,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
client = requests.Session()
client.mount("https://", adapter)
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

    json_list = glob.glob("%s*.json" % glob.escape(sourcefile))
    if json_list:
        if not args.usecache:
            # logger.info("Delete existed JSON file(s).")
            for jf in json_list:
                os.remove(jf)
        else:
            # logger.info("Skipping existed JSON file %s.json" % sourcefile)
            return 1, ""

    smart_parser_options = "-adapter prod -converted-storage-url http://disclosures.ru:8091"

    log = filepath + ".log"
    if os.path.exists(log):
        os.remove(log)

    cmd = "{} {} \"{}\"".format(
        SMART_PARSER,
        smart_parser_options,
        filepath.replace("`", "\\`"))
    return (datetime.now() - start_time).total_seconds(), os.popen(cmd).read()


def post_results(sourcefile, job, time_delta=None, skip_upload=False):
    df_id, archive_file = job.get('document_file', None), job.get('archive_file', None)
    filename = sourcefile[:sourcefile.rfind('.')]

    json_list = glob.glob("%s.json" % glob.escape(sourcefile))
    if len(json_list) == 1:
        # Properly constructed final JSON found
        data = json.load(open(json_list[0], encoding='utf8'))
    else:
        json_list = glob.glob("%s*.json" % glob.escape(sourcefile))
        if not json_list:
            # Build empty JSON to post report in API and skip parsing attemp in a future
            # print("Build empty JSON for %s" % sourcefile)
            data = {'document': {'documentfile_id': df_id}, 'persons': []}
            if archive_file:
                data['document']['archive_file'] = archive_file
        else:
            # Join separated JSON files (of XLSX lists)
            data = {'persons': [], 'document': {}}
            for json_file in json_list:
                file_data = json.load(open(json_file, encoding='utf8'))
                file_year = file_data.get('document', {}).get('year')

                expected_year = job.get('income_year', None)
                if file_year is not None and expected_year is not None and file_year != expected_year:
                    logger.warning("%s: Skip wrong declaration year %i (expected %i)" % (
                        json_file, file_year, expected_year))
                    continue
                data['persons'] += file_data['persons']
                # if data['document']:
                #     if data['document'].get('sheet_title') != file_data['document'].get('sheet_title'):
                #         logger.warning(
                #             "Document sheet title changed in one XLSX!")
                data['document'] = file_data['document']

    if 'sheet_number' in data['document']:
        del data['document']['sheet_number']

    try:
        data['document']['file_size'] = os.path.getsize(sourcefile)
    except:
        data['document']['file_size'] = 0

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
    result = job.copy()
    result['parser_log'] = data['document']['parser_log']
    result['sourcefile'] = sourcefile

    if not parsed:
        result['new_status'] = 'error'
    else:
        result['new_status'] = 'ok'

    if df_id:
        if job['status'] == 'ok' and not parsed:
            result['new_status'] = 'degrade'
        else:
            # logger.info("POSTing results (id=%i): %i persons, %i files, file_size %i" % (
            #     df_id, len(data['persons']), len(json_list), data['document']['file_size']))

            response = None
            if not skip_upload:
                while response is None:
                    try:
                        response = client.post(declarator_domain +
                                               '/api/jsonfile/validate/', data=body)
                    except requests.exceptions.ConnectionError:
                        logger.error("requests.exceptions.ConnectionError, retrying...")

                if response.status_code != requests.codes.ok:
                    logger.error(response)
                    logger.error(response.text)

    return result


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

    def run_job(self, job: dict):
        file_url, df_id, archive_file = (
            job.get('download_url', None),
            job.get('document_file', None),
            job.get('archive_file', None))

        if self.args.download_only:
            file_url = job.get("original_url")

        url_path, filename = os.path.split(file_url)
        filename, ext = os.path.splitext(filename)

        if archive_file:
            _, archive_ext = os.path.splitext(archive_file)
            file_path = os.path.join(
                self.args.output, str(df_id), archive_file)
            if archive_ext != ext:
                file_path += ext
        elif not df_id:
            # file_url is local path to file
            file_path = file_url
        else:
            file_path = os.path.join(self.args.output, "%i%s" % (df_id, ext))

        file_path = download_file(file_url, file_path)

        if self.args.download_only:
            return

        time_delta, parser_log = run_smart_parser(file_path, self.args)
        return post_results(file_path, job, time_delta, self.args.skip_upload)


def download_jobs(url=None, stop=False):
    """API call return list of files to parse (paged now)"""

    next_url = url
    while next_url:
        logger.info("GET Joblist URL: %s" % next_url)

        response = None
        while response is None:
            try:
                response = client.get(next_url)
            except requests.exceptions.ConnectionError:
                logger.error("requests.exceptions.ConnectionError, retrying...")
        try:
            result = json.loads(response.content.decode('utf-8'))
        except Exception as e:
            logger.error(response.content)
            raise e

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
        if name.startswith("~") and name.endswith(".doc"):
            continue
        joblist.append({
            "download_url": os.path.join(folder, name),
            "status": 'new'
        })
    return joblist


if __name__ == '__main__':
    args = parse_args()

    pool = Pool(args.parallel_pool_size)
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGINT, original_sigint_handler)

    joblist = args.joblist
    results = []

    try:
        if joblist.startswith('http'):
            joblist = list(download_jobs(joblist, stop=False))
        else:
            joblist = get_folder_jobs(joblist, args)

        if args.limit:
            joblist = joblist[:args.limit]

        logger.info("Starting %i jobs" % len(joblist))
        if len(joblist) == 1:
            res = ProcessOneFile(args, os.getpid())(joblist[0])
            results.append(res)
        elif len(joblist) == 0:
            logger.info("0 jobs found, exiting")
        else:
            iter_pool = pool.imap_unordered(ProcessOneFile(args, os.getpid()), joblist, chunksize=1)
            with tqdm.tqdm(iter_pool, total=len(joblist)) as t:
                for res in t:
                    results.append(res)
                    total = len(results)
                    ok = len(list(filter(lambda x: x['new_status'] == 'ok', results)))
                    upgraded = len(list(filter(lambda x: x['new_status'] == 'ok' and x['status'] == 'error', results)))
                    degraded = len(list(filter(lambda x: x['new_status'] == 'degrade', results)))
                    t.set_postfix(ok=ok, error=total - ok, upgraded=upgraded, degraded=degraded)

    except KeyboardInterrupt:
        logger.info("stop processing...")
        pool.terminate()
    else:
        print("Clean up")
        pool.close()

    total = len(results)

    if total == 0:
        sys.exit()

    ok = len(list(filter(lambda x: x['new_status'] == 'ok', results)))
    upgraded = len(list(filter(lambda x: x['new_status'] == 'ok' and x['status'] == 'error', results)))
    degraded_list = list(filter(lambda x: x['new_status'] == 'degrade', results))
    degraded = len(degraded_list)

    logger.info("Total files: %i" % (total,))
    logger.info("Succeed files: %i" % (ok,))
    logger.info("Errors: %i" % (total - ok))

    logger.info("Header_recall: %f" %
                (float(ok) / float(total)))
    logger.info("Header_recall was before re-parse: %f" %
                (float(len(list(filter(lambda x: x['status'] == 'ok', results)))) / float(total)))

    logger.info("Upgraded: %i" % (upgraded,))
    logger.info("Degraded: %i" % (degraded,))

    logger.info("Degraded list")
    for result in degraded_list:
        logger.info("file: %s " % (
            result['sourcefile'],
        ))
