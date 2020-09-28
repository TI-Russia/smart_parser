import argparse
import sys
import logging
import os
import time
import http.server
import io
import tarfile
from custom_http_codes import DLROBOT_HTTP_CODE
import shutil
import tarfile
import socket
import random


def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_worker")
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
    parser.add_argument("--log-file-name",  dest='log_file_name', required=False, default="dlrobot_worker.log")
    parser.add_argument("--tmp-folder",  dest='tmp_folder', required=True)
    parser.add_argument("--save-dlrobot-results",  dest='delete_dlrobot_results', default=True, action="store_false")
    parser.add_argument("--run-forever",  dest='run_forever', required=False, action="store_true", default=False)
    parser.add_argument("--timeout-before-next-task", dest='timeout_before_next_task', type=int, required=False, default=60)
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            default="3h",
                            help="crawling timeout (there is also conversion step after crawling, that takes time)")
    parser.add_argument("--only-send-back-this-project", dest='only_send_back_this_project', required=False)
    parser.add_argument("--http-put-timeout", dest='http_put_timeout', required=False, type=int, default=60*10)
    parser.add_argument("--fake-dlrobot", dest='fake_dlrobot', required=False, default=False, action="store_true")

    args = parser.parse_args()
    args.dlrobot_path = os.path.realpath(os.path.join(os.path.dirname(__file__ ), "../../dlrobot.py")).replace('\\', '/')
    assert os.path.exists (args.dlrobot_path)
    return args


def get_new_task_job(args, logger):
    conn = http.client.HTTPConnection(args.server_address)
    conn.request("GET", "?authorization_code=456788")
    response = conn.getresponse()
    conn.close()
    if response.status != http.HTTPStatus.OK:
        if response.status != DLROBOT_HTTP_CODE.NO_MORE_JOBS:
            logger.error("cannot get a new project from dlrobot central, httpcode={}".format(
                response.status
            ))
        return None
    project_file = response.getheader('dlrobot_project_file_name')
    if project_file is None:
        logger.error("cannot find filepath header")
        return None
    file_data = response.read()
    logger.debug("get task {} size={}".format(project_file, len(file_data)))
    basename_project_file = os.path.basename(project_file)
    base_folder, _ = os.path.splitext(basename_project_file)
    folder = os.path.join(args.tmp_folder, base_folder).replace('\\', '/')
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)

    logger.debug("mkdir {}".format(folder))
    os.makedirs(folder, exist_ok=True)

    logger.debug("write {}  to  {}".format(basename_project_file, folder))
    project_file = os.path.join(folder, basename_project_file)
    with open (project_file, "wb") as outp:
        outp.write(file_data)
    return project_file


def run_dlrobot(args, logger, project_file):

    project_folder = os.path.dirname(project_file).replace('\\', '/')
    if args.fake_dlrobot:
        with open(project_file  + ".dummy_random", "wb") as outp:
            outp.write(bytearray(random.getrandbits(8) for _ in range(200*1024*1024)))
        return 1

    cmd = 'bash -c "cd {}; export TMP=. ; /usr/bin/timeout 4h python3 {} --cache-folder-tmp --project {} --crawling-timeout {} --last-conversion-timeout 30m >dlrobot.out 2>dlrobot.err" '.format(
        project_folder, args.dlrobot_path, os.path.basename(project_file), args.crawling_timeout)
    logger.debug(cmd)
    exit_code = os.system(cmd)
    logger.debug("exit_code={}".format(exit_code))

    geckodriver_log = os.path.join(project_folder, "geckodriver.log")
    if exit_code == 0 and os.path.exists(geckodriver_log):
        os.unlink(geckodriver_log)
    goal_file = project_file + ".click_paths"
    if not os.path.exists(goal_file):
        exit_code = 1

    return exit_code


def send_results_back(args, logger, project_file, exitcode):
    project_folder = os.path.dirname(project_file)
    headers = {
        "exitcode" : exitcode,
        "dlrobot_project_file_name": os.path.basename(project_file),
        "Content-Type": "application/binary"
    }
    logger.debug("send results back for {} exitcode={}".format(project_file, exitcode))
    dlrobot_results_file_name = os.path.basename(project_file) + ".tar.gz"

    with tarfile.open(dlrobot_results_file_name, "w:gz") as tar:
        for f in os.listdir(project_folder):
            tar.add(os.path.join(project_folder, f), arcname=f)

    logger.debug("created file {} size={}".format(dlrobot_results_file_name, os.stat(dlrobot_results_file_name).st_size))

    for try_id in range(3):
        try:
            conn = http.client.HTTPConnection(args.server_address, timeout=args.http_put_timeout)
            with open(dlrobot_results_file_name, "rb") as inp:
                logger.debug("put file {} to {}".format(dlrobot_results_file_name, args.server_address))
                conn.request("PUT", dlrobot_results_file_name, inp.read(), headers=headers)
                response = conn.getresponse()
                conn.close()
                logger.debug("sent dlrobot result file {}, exitcode={}. size={}, http_code={}".format(
                    dlrobot_results_file_name,
                    exitcode,
                    os.stat(dlrobot_results_file_name).st_size,
                    response.status))
                break
        except Exception as error:
            conn.close()
            logger.error('Exception: %s, try_id={}', error, try_id)
            if try_id == 2:
                logger.debug("give up")
                raise

    logger.debug("delete file {}".format(dlrobot_results_file_name))
    os.unlink(dlrobot_results_file_name)

    if args.delete_dlrobot_results:
        shutil.rmtree(project_folder, ignore_errors=True)


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(args.log_file_name)
    if args.server_address is None:
        args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']

    if args.only_send_back_this_project is not None:
        send_results_back(args, logger, args.only_send_back_this_project, 0)
        sys.exit(0)

    running_project_file = None
    try:
        while True:
            running_project_file = None
            try:
                running_project_file = get_new_task_job(args, logger)
                if running_project_file is not None:
                    exit_code = run_dlrobot(args, logger, running_project_file)
                    send_results_back(args, logger, running_project_file, exit_code)
                    running_project_file = None
            except ConnectionError as err:
                logger.error(str(err))
            if not args.run_forever:
                break
            time.sleep(args.timeout_before_next_task)
        logger.info("successful exit")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("ctrl+c received")
    except Exception as exp:
        logger.error(exp)

    if running_project_file is not None:
        send_results_back(args, logger, running_project_file, 1)
    sys.exit(1)

x