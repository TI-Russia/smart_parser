from pssh.clients import ParallelSSHClient
import argparse
import sys
import logging
import os
from collections import defaultdict
import threading
import time
import queue
from  ConvStorage.conversion_client import TDocConversionClient

def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_parallel")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
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
    if os.name == "nt":
        pkey_default = "C:/Users/sokirko/.ssh/id_rsa"
    else:
        pkey_default = "/home/sokirko/.ssh/id_rsa"

    parser.add_argument("--hosts",  dest='hosts', required=True)
    parser.add_argument("--remote-folder", dest='remote_folder', default='/home/sokirko', required=False)
    parser.add_argument("--declarator-hdd-folder",  dest='declarator_hdd_folder', required=False, default="/home/sokirko/declarator_hdd")
    parser.add_argument("--smart-parser-folder", dest='smart_parser_folder', default='/home/sokirko/smart_parser',
                        required=False)
    parser.add_argument("--jobs-per-host", dest='jobs_per_host', default=4, required=False, type=int)
    parser.add_argument("--input-folder",  dest='input_folder', required=False, default="input_projects")
    parser.add_argument("--result-folder",  dest='result_folder', required=True)
    parser.add_argument("--username",  dest='username', required=False, default="sokirko")
    parser.add_argument("--pkey", dest='pkey', required=False, default=pkey_default)
    parser.add_argument("--retries-count", dest='retries_count', required=False, default=2, type=int)
    parser.add_argument("--initialize-worker", dest='initialize_worker', required=False,
                        default=os.path.join( os.path.dirname(__file__), "initialize_worker.py"))
    parser.add_argument("--job-script", dest='job_script',
                                    required=False,
                                    default=os.path.join(os.path.dirname(__file__), "one_site.py"))
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            default="3h",
                            help="crawling timeout in seconds (there is also conversion step after crawling)")

    args = parser.parse_args()
    assert os.path.exists(args.pkey)
    return args


def copy_file(pssh_client, filename, remote_path):
    assert os.path.exists(filename)

    greenlets = pssh_client.copy_file(filename, remote_path)
    for g in greenlets:
        try:
            logger.debug("copy task {}".format(" ".join(g.args[0:3])))
            res = g.get(10)
        except Exception as exp:
            logger.error("type(exception)={} exception={}".format(type(exp), exp))
            return False
    return True

def remote_path(args, filename):
    return os.path.join(args.remote_folder, os.path.basename(filename)).replace('\\', '/')


def prepare_hosts(args, logger):
    pssh_client = ParallelSSHClient(args.hosts.split(','), user=args.username, pkey=args.pkey)

    if not copy_file(pssh_client, args.initialize_worker, remote_path(args, args.initialize_worker) ):
        return False

    if not copy_file(pssh_client, args.job_script, remote_path(args, args.job_script) ):
        return False

    try:
        output = pssh_client.run_command(
            "python {} --declarator-hdd-folder {} --smart-parser-folder {}".format(
                remote_path(args, args.initialize_worker),
                args.declarator_hdd_folder,
                args.smart_parser_folder),
            stop_on_errors=True)
        pssh_client.join(output)
    except Exception as exp:
        logger.error("type(exception)={} exception={}".format(type(exp), exp))
        return False

    for host, host_output in output.items():
        logger.debug("host={}, exit code={}".format(host, host_output.exit_code))
        for line in host_output.stderr:
            logger.debug(host + " " + line)
        for line in host_output.stdout:
            logger.debug(host + " " + line)
        if host_output.exit_code != 0:
            return False
    return True


class TJobTasks:
    def __init__(self, args, logger):
        self.conversion_client =  TDocConversionClient(logger)
        self.args = args
        self.logger = logger
        self.host_tasks = defaultdict(set)
        for host in args.hosts.split(","):
            self.host_tasks[host] = set()
        assert len(self.host_tasks) > 0
        self.tries_count = defaultdict(int)
        self.lock = threading.Lock()
        self.input_files = queue.Queue()
        for x in os.listdir(args.input_folder):
            self.input_files.put(os.path.join(args.input_folder, x))
        logger.debug("we are going to process {} files".format(self.input_files.qsize()))
        self.threads = list()

    def get_free_host(self):
        while True:
            tasks = list( (len(v), k) for k, v in  self.host_tasks.items())
            tasks.sort()
            best_host_tasks = tasks[0][0]
            best_host = tasks[0][1]
            if best_host_tasks < self.args.jobs_per_host:
                return best_host
            time.sleep(20)

    def running_jobs_count(self):
        return sum(len(v) for v in self.host_tasks.values())

    def register_task(self, host, project_file):
        self.lock.acquire()
        try:
            self.host_tasks[host].add(project_file)
        finally:
            self.lock.release()

    def register_task_result(self, host, project_file, exit_code):
        self.lock.acquire()
        try:
            self.host_tasks[host].remove(project_file)
            self.tries_count[project_file] += 1
            if exit_code != 0:
                if self.tries_count[project_file] < args.retries_count:
                    self.input_files.put(project_file)
                    self.logger.debug("register retry for {}".format(project_file))
            else:
                self.logger.debug("success on {}".format(project_file))
        finally:
            self.lock.release()

    def run_job(self, host, project_file):
        pssh_client = ParallelSSHClient([host], user=self.args.username, pkey=self.args.pkey)
        remote_project_path = remote_path(args, project_file)
        if not copy_file(pssh_client, project_file, remote_project_path):
            return False

        cmd = "python3 {} --project-file {} --smart-parser-folder {} --result-folder {} --crawling-timeout {}".format(
            remote_path(args, self.args.job_script),
            remote_project_path,
            self.args.smart_parser_folder,
            self.args.result_folder,
            self.args.crawling_timeout
        )
        self.logger.debug('{}: {}'.format(host, cmd))
        output = pssh_client.run_command(cmd)
        pssh_client.join(output)
        if len(output.items()) == 0:
            self.register_task_result(host, project_file, 0)
            self.logger.error("no result for {} {}".format(host, project_file))
        else:
            for host, host_output in output.items():
                self.logger.debug("host={}, exit code={}".format(host, host_output.exit_code))
                for line in host_output.stderr:
                    self.logger.debug(host + " " + line)
                for line in host_output.stdout:
                    self.logger.debug(host + " " + line)
                self.register_task_result(host, project_file, host_output.exit_code)

    def stop_all_threads(self):
        for t in self.threads:
            t.join(1)
        self.threads = []

    def wait_conversion_pdf(self):
        while self.conversion_client.get_pending_all_file_size() > 100 * 2**20:
            self.logger.debug("wait 5 minutes till the conversion server finish its work")
            time.sleep(60 * 5)

    def run_jobs(self):
        count = 0
        while True:
            try:
                project_file = self.input_files.get(timeout=10)
            except Exception as exp:
                if self.running_jobs_count() > 0:
                    continue  #wait till all jobs finished
                if not self.input_files.empty():
                    self.logger("stop process, exception={}, left unfinished jobs".format(exp))
                    return False
                break
            host = self.get_free_host()
            self.wait_conversion_pdf()
            count += 1
            self.logger.info("start job: {}, left jobs: {}, running jobs: {}".format(count, \
                self.input_files.qsize(), self.running_jobs_count()))
            self.logger.info("process {} on {}".format(project_file, host))
            self.register_task(host, project_file)
            thread = threading.Thread(target=self.run_job, args=(host, project_file))
            thread.start()
            self.threads.append(thread)
            time.sleep(5)

        self.stop_all_threads()


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging("dlrobot_parallel.log")
    if not prepare_hosts(args, logger):
        sys.exit(1)
    job_tasks = TJobTasks(args, logger)
    try:
        job_tasks.run_jobs()
    except KeyboardInterrupt:
        print("ctrl+c received")
        sys.exit(1)
    finally:
        job_tasks.stop_all_threads()

