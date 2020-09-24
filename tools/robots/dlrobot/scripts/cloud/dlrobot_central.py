import argparse
import sys
import logging
import os
from collections import defaultdict
import time
from ConvStorage.conversion_client import TDocConversionClient
import json
import urllib
import http.server
import io, gzip, tarfile
from custom_http_codes import DLROBOT_HTTP_CODE
import threading
from robots.common.primitives import convert_timeout_to_seconds

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
    parser.add_argument("--log-file-name",  dest='log_file_name', required=False, default="dlrobot_central.log")
    parser.add_argument("--input-folder",  dest='input_folder', required=False, default="input_projects")
    parser.add_argument("--result-folder",  dest='result_folder', required=True)
    parser.add_argument("--retries-count", dest='retries_count', required=False, default=2, type=int)
    parser.add_argument("--read-previous-results", dest='read_previous_results', default=False, action='store_true',
                        required=False, help="read file dlrobot_results.dat and exclude succeeded tasks from the input tasks")

    parser.add_argument("--input-thread-timeout", dest='input_thread_timeout', required=False, default='20s')
    parser.add_argument("--dlrobot-project-timeout", dest='dlrobot_project_timeout',
                         required=False, default='4h')
    args = parser.parse_args()
    args.input_thread_timeout = convert_timeout_to_seconds(args.input_thread_timeout)
    args.dlrobot_project_timeout = convert_timeout_to_seconds(args.dlrobot_project_timeout)
    return args


class TRemoteDlrobotCall:

    def __init__ (self, worker_ip="", project_file="", exit_code=1):
        self.worker_ip = worker_ip
        self.project_file = project_file
        self.exit_code = exit_code
        self.start_time = int(time.time())
        self.end_time = int(time.time())

    def read_from_json(self, str):
        d = json.loads(str)
        self.worker_ip = d['worker_ip']
        self.project_file = d['project_file']
        self.exit_code = d['exit_code']
        self.start_time = d['start_time']
        self.end_time = d['end_time']

    def write_to_json(self):
        d =  {
                'worker_ip': self.worker_ip,
                'project_file' : self.project_file,
                'exit_code': self.exit_code,
                'start_time': self.start_time,
                'end_time': self.end_time
        }
        return json.dumps(d)


class TJobTasks:
    def __init__(self, args, logger):
        self.conversion_client = TDocConversionClient(logger)
        self.args = args
        self.logger = logger
        self.dlrobot_remote_calls = defaultdict(list)
        self.input_files = list(x for x in os.listdir(self.args.input_folder) if x.endswith('.txt'))
        if not os.path.exists(self.args.result_folder):
            os.makedirs(self.args.result_folder)

        if args.read_previous_results:
            self.read_prev_dlrobot_remote_calls()
        logger.debug("there are {} dlrobot projects to process".format(len(self.input_files)))
        self.worker_2_running_tasks = defaultdict(list)
        self.input_thread = None
        self.stop_input_thread = False

    def log_process_result(self, process_result):
        s = process_result.stdout.strip("\n\r ")
        if len(s) > 0:
            for line in s.split("\n"):
                self.logger.error("task stderr: {}".format(line))
        s = process_result.stderr.strip("\n\r ")
        if len(s) > 0:
            for line in s.split("\n"):
                self.logger.error("task stderr: {}".format(line))

    def get_dlrobot_remote_calls_filename(self):
        return os.path.join( self.args.result_folder, "dlrobot_remote_calls.dat")

    def save_dlrobot_remote_call(self, remote_call: TRemoteDlrobotCall):
        with open (self.get_dlrobot_remote_calls_filename(), "a") as outp:
            outp.write(remote_call.write_to_json() + "\n")
        self.dlrobot_remote_calls[remote_call.project_file].append(remote_call)
        if remote_call.exit_code != 0:
            if len(self.dlrobot_remote_calls[remote_call.project_file]) < args.retries_count:
                self.input_files.append(remote_call.project_file)
                self.logger.debug("register retry for {}".format(remote_call.project_file))

    def read_prev_dlrobot_remote_calls(self):
        self.logger.debug("read {}".format(self.get_dlrobot_remote_calls_filename()))
        with open(self.get_dlrobot_remote_calls_filename(), "r") as inp:
            for line in inp:
                line = line.strip()
                remote_call = TRemoteDlrobotCall()
                remote_call.read_from_json(line)
                self.dlrobot_remote_calls[remote_call.project_file].append(remote_call)
                if remote_call.exit_code == 0 and remote_call.project_file in self.input_files:
                    self.logger.debug("delete {}, since it is already processed".format(remote_call.project_file))
                    self.input_files.remove(remote_call.project_file)

    def running_jobs_count(self):
        return sum(len(w) for w in self.worker_2_running_tasks.values())

    def conversion_server_queue_is_short(self):
        input_queue_size = self.conversion_client.get_pending_all_file_size()
        self.logger.debug("conversion pdf input_queue_size={}".format(input_queue_size))
        return input_queue_size < 100 * 2**20

    def get_new_job_task(self, worker_ip):
        project_file = self.input_files.pop()
        self.logger.info("start job: {} on {}, left jobs: {}, running jobs: {}".format(
                project_file, worker_ip, len(self.input_files), self.running_jobs_count()))
        res = TRemoteDlrobotCall(worker_ip, project_file)
        self.worker_2_running_tasks[worker_ip].append(res)
        return project_file

    def untar_file(self, project_file, result_archive):
        base_folder, _ = os.path.splitext(project_file)
        output_folder = os.path.join(args.result_folder, base_folder)
        if os.path.exists(output_folder):
            output_folder += ".{}".format(int(time.time()))
        compressed_file = io.BytesIO(result_archive)
        decompressed_file = gzip.GzipFile(fileobj=compressed_file)
        tar = tarfile.open(fileobj=decompressed_file)
        tar.extractall(output_folder)

    def pop_project_from_running_tasks (self, worker_ip, project_file):
        if worker_ip not in self.worker_2_running_tasks:
            raise Exception("{} is missing in the worker table".format(worker_ip))
        worker_running_tasks = self.worker_2_running_tasks[worker_ip]
        for i in range(len(worker_running_tasks)):
            if worker_running_tasks[i].project_file == project_file:
                return worker_running_tasks.pop(i)
        raise Exception("{} is missing in the worker {} task table".format(project_file, worker_ip))

    def register_task_result(self, worker_ip, project_file, exit_code, result_archive):
        remote_call = self.pop_project_from_running_tasks(worker_ip, project_file)
        remote_call.exit_code = exit_code
        remote_call.end_time = int(time.time())
        self.save_dlrobot_remote_call(remote_call)
        self.untar_file(project_file, result_archive)

        self.logger.debug("got exitcode {} for task result {} from worker {}".format(
            exit_code, project_file, worker_ip))

    def start_input_files_thread(self):
        self.input_thread = threading.Thread(target=self.process_all_tasks, args=())
        self.input_thread.start()

    def stop_input_files_thread(self):
        self.stop_input_thread = True
        self.input_thread.join()

    def forget_old_remote_processes(self):
        curtime = time.time()
        for running_procs in self.worker_2_running_tasks.values():
            for i in range(len(running_procs) - 1, -1, -1):
                rc = running_procs[i]
                if curtime - rc.start_time > args.dlrobot_project_timeout:
                    self.logger.debug("task {} on worker {} takes {} seconds, probably it failed, stop waiting for a result".format(
                        rc.project_file, rc.worker_ip, curtime - rc.start_time
                    ))
                    running_procs.pop(i)
                    rc.exit_code = 126
                    rc.end_time = curtime
                    self.save_dlrobot_remote_call(rc)

    def process_all_tasks(self):
        while not self.stop_input_thread:
            time.sleep(args.input_thread_timeout)
            self.forget_old_remote_processes()

JOB_TASKS = None


class THttpServer(http.server.BaseHTTPRequestHandler):

    def parse_cgi(self, query_components):
        query = urllib.parse.urlparse(self.path).query
        if query == "":
            return True
        for qc in query.split("&"):
            items = qc.split("=")
            if len(items) != 2:
                return False
            query_components[items[0]] = items[1]
        return True

    def do_GET(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST):
            JOB_TASKS.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)
        global JOB_TASKS
        query_components = dict()
        if not self.parse_cgi(query_components):
            send_error('bad request')
            return
        dummy_code = query_components.get('authorization_code', None)
        if not dummy_code:
            send_error('No authorization_code provided')
            return

        if len(JOB_TASKS.input_files) == 0:
            send_error("no more jobs", DLROBOT_HTTP_CODE.NO_MORE_JOBS)
            return

        if not JOB_TASKS.conversion_server_queue_is_short():
            send_error("pdf conversion server is too busy", DLROBOT_HTTP_CODE.TOO_BUSY)
            return

        worker_ip = self.client_address[0]
        try:
            project_file = JOB_TASKS.get_new_job_task(worker_ip)
        except Exception as exp:
            send_error(str(exp))
            return

        self.send_response(200)
        self.send_header('dlrobot_project_file_name',  project_file)
        self.end_headers()

        file_path = os.path.join(JOB_TASKS.args.input_folder, project_file)
        with open(file_path, 'rb') as fh:
            self.wfile.write(fh.read())

    def do_PUT(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST):
            JOB_TASKS.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)

        global JOB_TASKS
        if self.path is None:
            send_error("no file specified")
            return

        _, file_extension = os.path.splitext(os.path.basename(self.path))
        file_length = int(self.headers['Content-Length'])
        filepath = self.headers.get('dlrobot_project_file_name')
        if filepath is None:
            send_error('cannot find header  dlrobot_project_file_name')
            return

        exitcode = self.headers.get('exitcode')
        if exitcode is None or not exitcode.isdigit():
            send_error('missing exitcode or bad exit code')
            return
        archive_file_bytes = self.rfile.read(file_length)
        worker_ip = self.client_address[0]

        try:
            JOB_TASKS.register_task_result(worker_ip, filepath, int(exitcode),  archive_file_bytes)
        except Exception as exp:
            send_error('register_task_result failed: {}'.format(str(exp)))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(args.log_file_name)
    if args.server_address is None:
        args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
    host, port = args.server_address.split(":")
    JOB_TASKS = TJobTasks(args, logger)
    JOB_TASKS.start_input_files_thread()
    if len(JOB_TASKS.input_files) == 0:
        logger.error("no more tasks")

    myServer = http.server.HTTPServer((host, int(port)), THttpServer)
    try:
        myServer.serve_forever()
    except KeyboardInterrupt:
        logger.info("ctrl+c received")
        JOB_TASKS.stop_input_files_thread()
        sys.exit(1)
    except Exception as exp:
        sys.stderr.write("general exception: {}\n".format(exp))
        logger.error("general exception: {}".format(exp))
        JOB_TASKS.stop_input_files_thread()
        sys.exit(1)

