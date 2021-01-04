from dlrobot_server.common_server_worker import DLROBOT_HTTP_CODE, TTimeouts, PITSTOP_FILE, DLROBOT_HEADER_KEYS
import argparse
import logging
import os
import sys
import time
import http.server
import shutil
import tarfile
import subprocess
import random
import signal
import tempfile
from concurrent.futures import ThreadPoolExecutor
import psutil
import threading
import platform

SCRIPT_DIR_NAME = os.path.realpath(os.path.dirname(__file__))
DLROBOT_PATH = os.path.realpath(os.path.join(SCRIPT_DIR_NAME, "../dl_robot/dlrobot.py")).replace('\\', '/')
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


def test_dlrobot_script(logger):
    proc = subprocess.Popen(
        ['/usr/bin/python3', DLROBOT_PATH, '--help'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ
        )
    proc.wait()
    logger.debug ("run dlrobot.py --help, exit_code={}".format(proc.returncode))
    return proc.returncode == 0


def check_system_resources(logger):
    total, used, free = shutil.disk_usage(os.curdir)
    if  free < 2 * 2**30:
        logger.error("no enough disk space")
        return False  #at least 2 GB free disk space must be available
    free_mem = psutil.virtual_memory().free
    if free_mem < 2*29:
        logger.error("no enough memory")
        return False  # at least 0.5 GB free memory
    return True


def delete_very_old_folders(logger):
    logger.debug("delete_very_old_folders")
    now = time.time()
    with os.scandir("") as it:
        for entry in it:
            if entry.is_dir() and entry.stat().st_mtime < now - TTimeouts.TIMEOUT_IN_WORKER_CLEAN_JUNK:
                logger.error("delete folder {} because it is too old, see TTimeouts.TIMEOUT_IN_WORKER_CLEAN_JUNK".format(entry.name))
                shutil.rmtree(str(entry.name), ignore_errors=True)


def stop():
    for proc in psutil.process_iter():
        cmdline = " ".join(proc.cmdline())
        if proc.pid != os.getpid():
            if 'dlrobot.py' in cmdline or 'firefox' in cmdline or 'dlrobot_worker.py' in cmdline:
                try:
                    proc.kill()
                except Exception as exp:
                    continue


def signal_term_handler(signum, frame):
    # to stop pool process
    raise Exception("the process was killed!")


class TDlrobotWorker:
    def __init__(self, args):
        self.args = args
        self.working = True
        self.thread_pool = ThreadPoolExecutor(max_workers=self.args.worker_count)
        self.setup_working_folder()
        self.logger = setup_logging(self.args.log_file_name)
        self.setup_environment()

    def setup_working_folder(self):
        if os.path.exists(self.args.working_folder):
            shutil.rmtree(self.args.working_folder, ignore_errors=True)
        os.makedirs(self.args.working_folder, exist_ok=True)
        # important
        os.chdir(self.args.working_folder)

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--home", dest='home', default=os.path.expanduser('~'), required=False,
                            help="home where smart_parser is installed")
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable DLROBOT_CENTRAL_SERVER_ADDRESS")
        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="dlrobot_worker.log")
        parser.add_argument("--working-folder",
                            dest='working_folder',
                            required=False,
                            default=os.path.join(tempfile.gettempdir(), "dlrobot_worker"))
        parser.add_argument("--save-dlrobot-results", dest='delete_dlrobot_results', default=True, action="store_false")
        parser.add_argument("--timeout-before-next-task", dest='timeout_before_next_task', type=int, required=False,
                            default=60)
        parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            type=int,
                            default=TTimeouts.MAIN_CRAWLING_TIMEOUT,
                            help="crawling timeout (there is also conversion step after crawling, that takes time)")
        parser.add_argument("--only-send-back-this-project", dest='only_send_back_this_project', required=False)
        parser.add_argument("--http-put-timeout", dest='http_put_timeout', required=False, type=int, default=60 * 10)
        parser.add_argument("--fake-dlrobot", dest='fake_dlrobot', required=False, default=False, action="store_true")
        parser.add_argument("--worker-count", dest='worker_count', default=2, type=int)
        parser.add_argument(dest='action', help="can be start, stop, restart, run_once")


        args = parser.parse_args(arg_list)
        return args

    def get_new_task_job(self):
        conn = http.client.HTTPConnection(self.args.server_address)
        headers = {
            DLROBOT_HEADER_KEYS.WORKER_HOST_NAME: platform.node(),
        }
        conn.request("GET", "?authorization_code=456788", headers=headers)
        response = conn.getresponse()
        conn.close()
        if response.status != http.HTTPStatus.OK:
            if response.status != DLROBOT_HTTP_CODE.NO_MORE_JOBS:
                self.logger.error("cannot get a new project from dlrobot central, httpcode={}".format(
                    response.status
                ))
            return
        project_file = response.getheader(DLROBOT_HEADER_KEYS.PROJECT_FILE)
        if project_file is None:
            self.logger.error("cannot find header {}".format(DLROBOT_HEADER_KEYS.PROJECT_FILE))
            return
        file_data = response.read()
        self.logger.debug("get task {} size={}".format(project_file, len(file_data)))
        basename_project_file = os.path.basename(project_file)
        folder, _ = os.path.splitext(basename_project_file)

        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
        self.logger.debug("mkdir {}".format(folder))
        os.makedirs(folder, exist_ok=True)

        self.logger.debug("write {}  to  {}".format(basename_project_file, folder))
        project_file = os.path.join(folder, basename_project_file)
        with open(project_file, "wb") as outp:
            outp.write(file_data)
        return project_file

    def clean_folder_before_archiving(self, project_folder, result_folder, exit_code):
        with os.scandir(project_folder) as it:
            for entry in it:
                if entry.is_dir() and entry.name != result_folder:
                    unknown_tmp_folder = os.path.join(project_folder, str(entry.name))
                    self.logger.debug("delete temp folder {}".format(unknown_tmp_folder))
                    shutil.rmtree(unknown_tmp_folder, ignore_errors=True)

        if exit_code == 0:
            geckodriver_log = os.path.join(project_folder, "geckodriver.log")
            if os.path.exists(geckodriver_log):
                os.unlink(geckodriver_log)
        else:
            folder = os.path.join(project_folder, result_folder)
            if os.path.exists(folder):
                self.logger.debug("delete folder {} since dlrobot failed".format(folder))
                shutil.rmtree(folder, ignore_errors=True)

    def run_dlrobot(self, project_file):
        project_folder = os.path.dirname(os.path.realpath(project_file)).replace('\\', '/')
        if self.args.fake_dlrobot:
            with open(project_file + ".dummy_random", "wb") as outp:
                outp.write(bytearray(random.getrandbits(8) for _ in range(200 * 1024 * 1024)))
            return 1

        my_env = os.environ.copy()
        my_env['TMP'] = project_folder
        my_env['TMPDIR'] = project_folder
        exit_code = 1
        result_folder = "result"
        try:
            dlrobot_call = [
                '/usr/bin/python3',
                DLROBOT_PATH,
                '--cache-folder-tmp',
                '--project', os.path.basename(project_file),
                '--crawling-timeout', str(self.args.crawling_timeout),
                '--last-conversion-timeout', str(TTimeouts.WAIT_CONVERSION_TIMEOUT),
                '--result-folder', "result",
                '--total-timeout', str(TTimeouts.OVERALL_HARD_TIMEOUT_IN_WORKER)
            ]
            self.logger.debug(" ".join(dlrobot_call))
            with open(os.path.join(project_folder, "dlrobot.out"), "w") as dout:
                with open(os.path.join(project_folder, "dlrobot.err"), "w") as derr:
                    proc = subprocess.Popen(
                        dlrobot_call,
                        stdout=dout,
                        stderr=derr,
                        env=my_env,
                        cwd=project_folder,
                        text=True)
            proc.wait(TTimeouts.OVERALL_HARD_TIMEOUT_IN_WORKER)  # 4 hours
            exit_code = proc.returncode

        except subprocess.TimeoutExpired as exp:
            self.logger.error("wait raises timeout exception:{},  timeout={}".format(
                str(exp), TTimeouts.OVERALL_HARD_TIMEOUT_IN_WORKER))
        except Exception as exp:
            self.logger.error(exp)

        self.logger.debug("{} exit_code={}".format(project_file, exit_code))
        # up to now we do not need a .click_paths file, but this file is written at the very end (after file export)
        goal_file = project_file + ".click_paths"
        if not os.path.exists(goal_file):
            self.logger.debug("set exit code=1, since {} not found".format(goal_file))
            exit_code = 1

        self.clean_folder_before_archiving(project_folder, result_folder, exit_code)

        if exit_code != 0:
            # this pkill was not tested
            cmd = "pkill -f \"project {}\"".format(project_file)
            self.logger.debug(cmd)
            os.system(cmd)

        return exit_code

    def send_results_back(self, project_file, exitcode):
        project_folder = os.path.dirname(project_file)
        headers = {
            DLROBOT_HEADER_KEYS.EXIT_CODE: exitcode,
            DLROBOT_HEADER_KEYS.PROJECT_FILE: os.path.basename(project_file),
            DLROBOT_HEADER_KEYS.WORKER_HOST_NAME: platform.node(),
            "Content-Type": "application/binary"
        }
        self.logger.debug("send results back for {} exitcode={}".format(project_file, exitcode))
        dlrobot_results_file_name = os.path.basename(project_file) + ".tar.gz"

        with tarfile.open(dlrobot_results_file_name, "w:gz") as tar:
            for f in os.listdir(project_folder):
                tar.add(os.path.join(project_folder, f), arcname=f)

        self.logger.debug(
            "created file {} size={}".format(dlrobot_results_file_name, os.stat(dlrobot_results_file_name).st_size))

        for try_id in range(3):
            conn = None
            try:
                conn = http.client.HTTPConnection(self.args.server_address, timeout=self.args.http_put_timeout)
                with open(dlrobot_results_file_name, "rb") as inp:
                    self.logger.debug("put file {} to {}".format(dlrobot_results_file_name, self.args.server_address))
                    conn.request("PUT", dlrobot_results_file_name, inp.read(), headers=headers)
                    response = conn.getresponse()
                    conn.close()
                    conn = None
                    self.logger.debug("sent dlrobot result file {}, exitcode={}. size={}, http_code={}".format(
                        dlrobot_results_file_name,
                        exitcode,
                        os.stat(dlrobot_results_file_name).st_size,
                        response.status))
                    break
            except Exception as error:
                if conn is not None:
                    conn.close()
                self.logger.error('Exception: {}, try_id={}', str(error), try_id)
                if try_id == 2:
                    self.logger.debug("give up")
                    raise

        self.logger.debug("delete file {}".format(dlrobot_results_file_name))
        os.unlink(dlrobot_results_file_name)

        if self.args.delete_dlrobot_results:
            shutil.rmtree(project_folder, ignore_errors=True)

    def ping_central(self):
        self.logger.debug("pinging {}".format(self.args.server_address))
        try:
            conn = http.client.HTTPConnection(self.args.server_address)
            conn.request("GET", "/ping")
            response = conn.getresponse()
            self.logger.debug("response status = {}".format(response.status))
            if response.status != http.HTTPStatus.OK:
                self.logger.error("dlrobot central does not answer")
            answer = response.read().decode("utf8").strip()
            conn.close()
        except Exception as exp:
            self.logger.error(exp)
            return False
        if answer != "pong":
            self.logger.error("ping dlrobot central, answer={}, must be 'pong'".format(answer))
            return False
        self.logger.debug("dlrobot_central is alive")
        return True

    def setup_environment(self):
        self.logger.debug("current dir: {}".format(os.path.realpath(os.path.curdir)))
        os.environ['ASPOSE_LIC'] = os.path.join(self.args.home, "lic.bin")
        os.environ['PYTHONPATH'] = os.path.join(self.args.home, "smart_parser/tools")
        os.environ['DECLARATOR_CONV_URL'] = "disclosures.ru:8091"
        self.logger .debug("PYTHONPATH={}".format(os.environ.get("PYTHONPATH")))

        if self.args.server_address is None:
            self.args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
        self.ping_central()
        assert (test_dlrobot_script(self.logger))
        if self.args.action == "run_once":
            self.args.worker_count = 1
        geckodriver = shutil.which("geckodriver")
        if geckodriver is None:
            raise Exception("cannot find geckodriver (selenium)")

        if os.path.exists(PITSTOP_FILE):
            os.unlink(PITSTOP_FILE)

    def run_dlrobot_and_send_results_in_thread(self):
        while self.working:
            if os.path.exists(PITSTOP_FILE):
                self.logger.debug("exit because file {} exists".format(PITSTOP_FILE))
                break
            if not threading.main_thread().is_alive():
                break

            timeout = self.args.timeout_before_next_task

            if not check_system_resources(self.logger):
                delete_very_old_folders(self.logger)
                if not check_system_resources(self.logger):
                    self.logger.debug("check_system_resources failed, sleep 10 minutes")
                    timeout = 60 * 10  # there is a hope that the second process frees the disk
            else:
                try:
                    project_file = self.get_new_task_job()
                    if project_file is not None:
                        exit_code = self.run_dlrobot(project_file)
                        timeout = 0
                        if self.working:
                            self.send_results_back(project_file, exit_code)
                except ConnectionError as err:
                    self.logger.error(str(err))
            if self.args.action == "run_once":
                break
            if timeout > 0:
                time.sleep(timeout)

    def run_thread_pool(self):
        self.logger.debug("start {} workers".format(self.args.worker_count))
        futures = list()
        for i in range(self.args.worker_count):
            f = self.thread_pool.submit(self.run_dlrobot_and_send_results_in_thread)
            futures.append(f)
        for f in futures:
            future_result = f.result() #wait
        self.logger.debug("exit run_thread_pool")

    def stop_worker(self):
        self.working = False
        self.thread_pool.shutdown()


if __name__ == "__main__":
    args = TDlrobotWorker.parse_args(sys.argv[1:])
    if args.action == "stop":
        stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_term_handler)
    client = TDlrobotWorker(args)
    if args.only_send_back_this_project is not None:
        client.send_results_back(args.only_send_back_this_project, 0)
        sys.exit(0)

    try:
        client.run_thread_pool()
        sys.exit(0)
    except KeyboardInterrupt:
        client.logger.info("ctrl+c received")
    except Exception as exp:
        client.logger.error(exp)
    finally:
        client.working = False
        if os.path.exists(PITSTOP_FILE):
            os.unlink(PITSTOP_FILE)
        client.stop_worker()
