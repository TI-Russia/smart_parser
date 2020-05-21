import argparse
import sys
import logging
import os
from collections import defaultdict
import threading
import time
import queue
from  ConvStorage.conversion_client import TDocConversionClient
from pssh.utils import logger as pssh_logger
import re
import subprocess


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

    pssh_logger.setLevel(logging.DEBUG)
    pssh_logger.addHandler(fh)

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
    parser.add_argument("--ssh-port", dest='ssh_port', required=False, default=None)
    parser.add_argument("--retries-count", dest='retries_count', required=False, default=2, type=int)
    parser.add_argument("--exclude-from-log", dest='old_log_file_list', action='append', required=False,
                        help="read this log file and exclude succeeded tasks from the imput tasks")
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






class TWorkerHost:
    def __init__(self, args, logger, hostname):
        self.logger = logger
        self.hostname = hostname
        self.tasks = set()


class TJobTasks:
    def __init__(self, args, logger):
        self.conversion_client = TDocConversionClient(logger)
        self.args = args
        self.logger = logger
        self.host_workers = dict((hostname, TWorkerHost(args, logger, hostname)) for hostname in args.hosts.split(","))
        assert len(self.host_workers) > 0
        self.tries_count = defaultdict(int)
        self.lock = threading.Lock()
        self.input_files = queue.Queue()
        for x in self.get_input_files():
            self.input_files.put(os.path.join(args.input_folder, x))
        logger.debug("we are going to process {} files".format(self.input_files.qsize()))
        self.threads = list()

    def remote_path(self, filename):
        return os.path.join(self.args.remote_folder, os.path.basename(filename)).replace('\\', '/')

    def log_process_result(self, process_result):
        s = process_result.stdout.strip("\n\r ")
        if len(s) > 0:
            for line in s.split("\n"):
                self.logger.error("task stderr: {}".format(line))
        s = process_result.stderr.strip("\n\r ")
        if len(s) > 0:
            for line in s.split("\n"):
                self.logger.error("task stderr: {}".format(line))

    def copy_file(self, filename, hostname, timeout=20):
        if not os.path.exists(filename):
            self.logger.error("cannot find {}".format(filename))
            assert os.path.exists(filename)
        remote_file_path = "{}:{}".format(hostname, self.remote_path(filename))
        scp_args = ['scp', '-i', args.pkey]
        if args.ssh_port is not None:
            scp_args += ['-P', args.ssh_port]
        scp_args += [filename, remote_file_path]
        self.logger.debug(" ".join(scp_args))
        try:
            child = subprocess.run(scp_args, encoding="utf8", timeout=timeout, check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exp:
            self.logger.error("copy task {} failed, exception {}".format(" ".join(scp_args), exp))
            self.log_process_result(exp)
            return False

    def run_remote_command(self, hostname, command, log_output=False):
        ssh_args = ['ssh', '-i', args.pkey]
        if args.ssh_port is not None:
            ssh_args += ['-p', args.ssh_port]
        assert command.find('"') == -1
        ssh_args += [hostname, command]
        self.logger.debug(" ".join(ssh_args))
        try:
            child = subprocess.run(ssh_args, encoding="utf8", errors="ignore", check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if log_output:
                self.log_process_result(child)
            return child.returncode
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exp:
            self.logger.error("task {} failed, exception {}".format(" ".join(ssh_args), exp))
            self.log_process_result(exp)
            if hasattr(exp, "returncode"):
                return exp.returncode
            else:
                return 1

    def prepare_hosts(self):
        for hostname in self.host_workers.keys():
            if not self.copy_file(args.initialize_worker, hostname):
                return False
            if not self.copy_file(args.job_script, hostname):
                return False

            cmd = "python {} --declarator-hdd-folder {} --smart-parser-folder {}".format(
                self.remote_path(args.initialize_worker),
                args.declarator_hdd_folder,
                args.smart_parser_folder)
            if self.run_remote_command(hostname, cmd) != 0:
                return False
        return True

    def get_free_host(self):
        while True:
            tasks = list( (len(host_worker.tasks), hostname) for hostname, host_worker in self.host_workers.items())
            tasks.sort()
            best_host_tasks = tasks[0][0]
            best_host = tasks[0][1]
            if best_host_tasks < self.args.jobs_per_host:
                return best_host
            time.sleep(20)

    def get_input_files(self):
        already_processed = set()
        if args.old_log_file_list is not None:
            for  old_log_file in args.old_log_file_list:
                with open(old_log_file, "r", encoding="utf8") as inp:
                    for line in inp:
                        line= line.strip(" \n\r")
                        m = re.search('success on (.+txt)$', line)
                        if m:
                            filename = os.path.basename(m.group(1))
                            already_processed.add(filename)
        for x in os.listdir(self.args.input_folder):
            if x in already_processed:
                self.logger.debug("exclude {}, already processed".format(x))
            else:
                yield x

    def running_jobs_count(self):
        return sum(len(w.tasks) for w in self.host_workers.values())

    def register_task(self, host, project_file):
        self.lock.acquire()
        try:
            self.host_workers[host].tasks.add(project_file)
        finally:
            self.lock.release()

    def register_task_result(self, host, project_file, exit_code):
        self.lock.acquire()
        try:
            self.host_workers[host].tasks.remove(project_file)
            self.tries_count[project_file] += 1
            if exit_code != 0:
                if self.tries_count[project_file] < args.retries_count:
                    self.input_files.put(project_file)
                    self.logger.debug("register retry for {}".format(project_file))
            else:
                self.logger.debug("success on {}".format(project_file))
        finally:
            self.lock.release()

    def run_job(self, hostname, project_file):
        if not self.copy_file(project_file, hostname):
            return False

        cmd = "python3 {} --project-file {} --smart-parser-folder {} --result-folder {} --crawling-timeout {}".format(
            self.remote_path(self.args.job_script),
            self.remote_path(project_file),
            self.args.smart_parser_folder,
            self.args.result_folder,
            self.args.crawling_timeout
        )
        exit_code = self.run_remote_command(hostname, cmd, log_output=True)
        self.register_task_result(hostname, project_file, exit_code)

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

    job_tasks = TJobTasks(args, logger)
    if not job_tasks.prepare_hosts():
        sys.exit(1)
    try:
        job_tasks.run_jobs()
    except KeyboardInterrupt:
        print("ctrl+c received")
        sys.exit(1)
    finally:
        job_tasks.stop_all_threads()

