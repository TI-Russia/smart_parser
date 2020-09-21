import argparse
import sys
import logging
import os
from collections import defaultdict
import time
from  ConvStorage.conversion_client import TDocConversionClient
import re
import http.server
import io, gzip, tarfile
from custom_http_codes import DLROBOT_HTTP_CODE
import shutil
import tarfile

def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_parallel")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", dest='server_address', default=None, help="by default read it from environment variable DLROBOT_CENTRAL_SERVER_ADDRESS")
    parser.add_argument("--log-file-name",  dest='log_file_name', required=False, default="dlrobot_parallel.log")
    parser.add_argument("--tmp-folder",  dest='tmp_folder', required=True)
    parser.add_argument("--run-forever",  dest='run_forever', required=False, action=)
    parser.add_argument("--timeout", dest='timeout', type=int, required=False, default=60*5)
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            default="3h",
                            help="crawling timeout in seconds (there is also conversion step after crawling)")
    args = parser.parse_args()
    return args



def get_new_task_job(args, logger):
    conn = http.client.HTTPConnection(args.server_address)
    conn.request("GET", "?authorization_code=456788")
    response = conn.getresponse()
    if response.status != http.HTTPStatus.OK:
        if response.status != DLROBOT_HTTP_CODE.NO_MORE_JOBS:
            logger.error("cannot get a new project from dlrobot central, httpcode={}".format(
                response.status
            ))
            return None, None
    project_file = response.getheader('dlrobot_project_file_name')
    if project_file is None:
        logger.error("cannot find filepath header")
        return None, None
    file_data = response.read()
    logger.debug("get task {} size={}".format(project_file, len(file_data)))
    basename_project_file = os.path.basename(project_file)
    base_folder, _ = os.path.splitext(basename_project_file)
    folder = os.path.join(args.tmp_folder, base_folder)
    os.makedirs(folder, exist_ok=True)
    local_project_file = os.path.join(folder, basename_project_file)
    with open (local_project_file, "wb") as outp:
        outp.write(file_data)
    return local_project_file


def run_dlrobot(args, logger, project_file):
    os.chdir(os.path.dirname(project_file))
    dlrobot = os.path.join(os.path.dirname(__file__ ), "../../dlrobot.py")
    cmd = "export TMP=. ; timeout 4h python3 {} --project {} --crawling-timeout {} --last-conversion-timeout 30m >dlrobot.out 2>dlrobot.err".format(
        dlrobot, project_file, args.crawling_timeout)
    exit_code = os.system(cmd)
    if os.path.exists("cached"):
        shutil.rmtree("cached", ignore_errors=True)
    if exit_code == 0 and os.path.exists("geckodriver.log"):
        os.unlink("geckodriver.log")
    goal_file = project_file + ".clicks.stats"
    if not os.path.exists(goal_file):
        logger.error("cannot find {}, dlrobot.py failed, delete result folder".format(goal_file))
        exit_code = 1
        shutil.rmtree("result", ignore_errors=True)

    return exit_code


def send_results_back(args, logger, project_file, exitcode):
    os.chdir("..")
    basename_project_file = os.path.basename(project_file)
    base_folder, _ = os.path.splitext(basename_project_file)
    headers = {
        "exitcode" : exitcode,
        "dlrobot_project_file_name": os.path.basename(project_file)
    }
    conn = http.client.HTTPConnection(args.server_address)
    if exitcode == 0:
        dlrobot_results_file_name = base_folder + ".tar.gz"
        with tarfile.open(dlrobot_results_file_name, "w:gz") as tar:
            tar.add(base_folder)
        with open(dlrobot_results_file_name, "rb") as inp:
            conn.request("PUT", dlrobot_results_file_name, inp.read(), headers=headers)
            response = conn.getresponse()
            logger.debug("sent dlrobot result file {}, size={}, http_code={}".format(
                dlrobot_results_file_name,
                os.stat(dlrobot_results_file_name).st_size,
                response.status))
    else:
        conn.request("PUT", "error", "", headers={"exitcode": exitcode})
        response = conn.getresponse()
        logger.error("sent dlrobot error, input_project={}, exitcode={} http_code={}".format(
            basename_project_file,
            exitcode,
            response.status))
    return base_folder


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(args.log_file_name)
    if args.server_address is None:
        args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']

    try:
        while True:
            try:
                project_file = get_new_task_job(args, logger)
                if project_file is not None:
                    exit_code = run_dlrobot(args, logger, project_file)
                    base_folder = send_results_back(args, logger, project_file, exit_code)
                    shutil.rmtree(base_folder, ignore_errors=True)
            except ConnectionError as err:
                logger.error(str(err))

            time.sleep(args.timeout)
    except KeyboardInterrupt:
        logger.info("ctrl+c received")
        sys.exit(1)

