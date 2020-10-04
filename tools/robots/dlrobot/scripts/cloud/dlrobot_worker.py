import argparse
import sys
import logging
import os
import time
import http.server
from common_server_worker import DLROBOT_HTTP_CODE, TTimeouts, PITSTOP_FILE, DLROBOT_HEADER_KEYS
import shutil
import tarfile
import subprocess
import random
import signal
import tempfile
from multiprocessing import Pool
from functools import partial
import psutil
import threading
import platform

SCRIPT_DIR_NAME = os.path.realpath(os.path.dirname(__file__))
DLROBOT_PATH = os.path.realpath(os.path.join(SCRIPT_DIR_NAME, "../../dlrobot.py")).replace('\\', '/')
assert os.path.exists(DLROBOT_PATH)


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
    parser.add_argument("--home", dest='home', default=os.path.expanduser('~'), required=False,  help="home where smart_parser is installed")
    parser.add_argument("--server-address", dest='server_address', default=None, help="by default read it from environment variable DLROBOT_CENTRAL_SERVER_ADDRESS")
    parser.add_argument("--log-file-name",  dest='log_file_name', required=False, default="dlrobot_worker.log")
    parser.add_argument("--working-folder",
                            dest='working_folder',
                            required=False,
                            default=os.path.join(tempfile.gettempdir(), "dlrobot_worker"))
    parser.add_argument("--save-dlrobot-results",  dest='delete_dlrobot_results', default=True, action="store_false")
    parser.add_argument("--timeout-before-next-task", dest='timeout_before_next_task', type=int, required=False, default=60)
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            type=int,
                            default=TTimeouts.MAIN_CRAWLING_TIMEOUT,
                            help="crawling timeout (there is also conversion step after crawling, that takes time)")
    parser.add_argument("--only-send-back-this-project", dest='only_send_back_this_project', required=False)
    parser.add_argument("--http-put-timeout", dest='http_put_timeout', required=False, type=int, default=60*10)
    parser.add_argument("--fake-dlrobot", dest='fake_dlrobot', required=False, default=False, action="store_true")
    parser.add_argument("--worker-count", dest='worker_count', default=2, type=int)
    parser.add_argument(dest='action', help="can be start, stop, restart, run_once")

    args = parser.parse_args()
    return args


def test_dlrobot_script(args):
    proc = subprocess.Popen(
        ['/usr/bin/python3', DLROBOT_PATH, '--help'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ
        )
    exit_code = proc.wait()
    args.logger.debug ("exit_code=".format(exit_code))
    return exit_code == 0


def ping_central(args):
    args.logger.debug("pinging {}".format(args.server_address))
    try:
        conn = http.client.HTTPConnection(args.server_address)
        conn.request("GET", "/ping")
        response = conn.getresponse()
        args.logger.debug("response status = {}".format(response.status))
        if response.status != http.HTTPStatus.OK:
            args.logger.error("dlrobot central does not answer")
        answer = response.read().decode("utf8").strip()
    except Exception as exp:
        args.logger.error(exp)
        return False
    if answer != "pong":
        args.logger.error("ping dlrobot central, answer={}, must be 'pong'".format(answer))
        return False
    args.logger.debug("dlrobot_central is alive")
    return True


def setup_environment(args):
    sys.stderr.write ("home folder = {}, working folder={}\n".format(args.home, args.working_folder))

    if os.path.exists(args.working_folder):
        shutil.rmtree(args.working_folder, ignore_errors=True)
    os.makedirs(args.working_folder, exist_ok=True)

    # important
    os.chdir(args.working_folder)

    args.logger = setup_logging(args.log_file_name)
    args.logger.debug("current dir: {}".format(os.path.realpath(os.path.curdir)))

    os.environ['ASPOSE_LIC'] =  os.path.join(args.home, "lic.bin")
    os.environ['PYTHONPATH'] = os.path.join(args.home, "smart_parser/tools")
    os.environ['DECLARATOR_CONV_URL'] = "disclosures.ru:8091"
    args.logger.debug("PYTHONPATH={}".format(os.environ.get("PYTHONPATH")))

    if args.server_address is None:
        args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
    ping_central(args)
    assert (test_dlrobot_script(args))
    if args.action == "run_once":
        args.worker_count = 1
    geckodriver = shutil.which("geckodriver")
    if geckodriver is None:
        raise Exception("cannot find geckodriver (selenium)")


def get_new_task_job(args):
    conn = http.client.HTTPConnection(args.server_address)
    headers = {
        DLROBOT_HEADER_KEYS.WORKER_HOST_NAME : platform.node(),
    }
    conn.request("GET", "?authorization_code=456788", headers=headers)
    response = conn.getresponse()
    conn.close()
    if response.status != http.HTTPStatus.OK:
        if response.status != DLROBOT_HTTP_CODE.NO_MORE_JOBS:
            args.logger.error("cannot get a new project from dlrobot central, httpcode={}".format(
                response.status
            ))
        return
    project_file = response.getheader(DLROBOT_HEADER_KEYS.PROJECT_FILE)
    if project_file is None:
        args.logger.error("cannot find header {}".format(DLROBOT_HEADER_KEYS.PROJECT_FILE))
        return
    file_data = response.read()
    args.logger.debug("get task {} size={}".format(project_file, len(file_data)))
    basename_project_file = os.path.basename(project_file)
    folder, _ = os.path.splitext(basename_project_file)

    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)
    args.logger.debug("mkdir {}".format(folder))
    os.makedirs(folder, exist_ok=True)

    args.logger.debug("write {}  to  {}".format(basename_project_file, folder))
    project_file = os.path.join(folder, basename_project_file)
    with open (project_file, "wb") as outp:
        outp.write(file_data)
    return project_file


def run_dlrobot(args,  project_file):
    project_folder = os.path.dirname(os.path.realpath(project_file)).replace('\\', '/')
    if args.fake_dlrobot:
        with open(project_file  + ".dummy_random", "wb") as outp:
            outp.write(bytearray(random.getrandbits(8) for _ in range(200*1024*1024)))
        return 1

    my_env = os.environ.copy()
    my_env['TMP'] = project_folder
    exit_code = 1
    try:
        dlrobot_call = [
                '/usr/bin/python3',
                DLROBOT_PATH,
                '--cache-folder-tmp',
                '--project',  os.path.basename(project_file),
                '--crawling-timeout',  str(args.crawling_timeout),
                '--last-conversion-timeout',  str(TTimeouts.WAIT_CONVERSION_TIMEOUT)

            ]
        args.logger.debug(" ".join(dlrobot_call))
        with open(os.path.join(project_folder, "dlrobot.out"), "w") as dout:
            with open(os.path.join(project_folder, "dlrobot.err"), "w") as derr:
                proc = subprocess.Popen(
                    dlrobot_call,
                    stdout=dout,
                    stderr=derr,
                    env=my_env,
                    cwd=project_folder,
                    text=True)
        exit_code = proc.wait(TTimeouts.OVERALL_HARD_TIMEOUT_IN_WORKER) # 4 hours

    except subprocess.TimeoutExpired as exp:
        args.logger.error("wait raises timeout exception:{},  timeout={}".format(
            str(exp), TTimeouts.OVERALL_HARD_TIMEOUT_IN_WORKER))
    except Exception as exp:
        args.logger.error(exp)

    args.logger.debug("exit_code={}".format(exit_code))

    geckodriver_log = os.path.join(project_folder, "geckodriver.log")
    if exit_code == 0 and os.path.exists(geckodriver_log):
        os.unlink(geckodriver_log)
    goal_file = project_file + ".click_paths"
    if not os.path.exists(goal_file):
        exit_code = 1

    return exit_code


def send_results_back(args, project_file, exitcode):
    project_folder = os.path.dirname(project_file)
    headers = {
        DLROBOT_HEADER_KEYS.EXIT_CODE: exitcode,
        DLROBOT_HEADER_KEYS.PROJECT_FILE: os.path.basename(project_file),
        DLROBOT_HEADER_KEYS.WORKER_HOST_NAME : platform.node(),
        "Content-Type": "application/binary"
    }
    args.logger.debug("send results back for {} exitcode={}".format(project_file, exitcode))
    dlrobot_results_file_name = os.path.basename(project_file) + ".tar.gz"

    with tarfile.open(dlrobot_results_file_name, "w:gz") as tar:
        for f in os.listdir(project_folder):
            tar.add(os.path.join(project_folder, f), arcname=f)

    args.logger.debug("created file {} size={}".format(dlrobot_results_file_name, os.stat(dlrobot_results_file_name).st_size))

    for try_id in range(3):
        try:
            conn = http.client.HTTPConnection(args.server_address, timeout=args.http_put_timeout)
            with open(dlrobot_results_file_name, "rb") as inp:
                args.logger.debug("put file {} to {}".format(dlrobot_results_file_name, args.server_address))
                conn.request("PUT", dlrobot_results_file_name, inp.read(), headers=headers)
                response = conn.getresponse()
                conn.close()
                args.logger.debug("sent dlrobot result file {}, exitcode={}. size={}, http_code={}".format(
                    dlrobot_results_file_name,
                    exitcode,
                    os.stat(dlrobot_results_file_name).st_size,
                    response.status))
                break
        except Exception as error:
            conn.close()
            args.logger.error('Exception: %s, try_id={}', error, try_id)
            if try_id == 2:
                args.logger.debug("give up")
                raise

    args.logger.debug("delete file {}".format(dlrobot_results_file_name))
    os.unlink(dlrobot_results_file_name)

    if args.delete_dlrobot_results:
        shutil.rmtree(project_folder, ignore_errors=True)


def run_dlrobot_and_send_results_in_thread(args, process_id):
    while True:
        running_project_file = None
        if os.path.exists(PITSTOP_FILE):
            break
        if not threading.main_thread().is_alive():
            break
        try:
            running_project_file = get_new_task_job(args)
            if running_project_file is not None:
                exit_code = run_dlrobot(args,  running_project_file)
                send_results_back(args,  running_project_file, exit_code)
        except ConnectionError as err:
            args.logger.error(str(err))
        if args.action == "run_once":
            break
        if running_project_file is None:
            time.sleep(args.timeout_before_next_task)


def stop(args):
    for proc in psutil.process_iter():
        cmdline = " ".join(proc.cmdline())
        if proc.pid != os.getpid():
            if 'dlrobot_worker.py' in cmdline or 'firefox' in cmdline:
                proc.kill()


def signal_term_handler(signum, frame):
    # to stop pool process
    raise Exception("the process was killed!")


if __name__ == "__main__":
    args = parse_args()
    if args.action == "stop":
        stop(args)
        sys.exit(0)
    setup_environment(args)
    if args.only_send_back_this_project is not None:
        send_results_back(args, args.only_send_back_this_project, 0)
        sys.exit(0)
    running_project_file = None
    pool = Pool(args.worker_count)
    signal.signal(signal.SIGTERM, signal_term_handler)
    try:
        res = pool.map(partial(run_dlrobot_and_send_results_in_thread, args), range(args.worker_count))
        sys.exit(0)
    except KeyboardInterrupt:
        args.logger.info("ctrl+c received")
    except Exception as exp:
        args.logger.error(exp)
    finally:
        pool.close()
        print("pool terminate")
        pool.terminate()

