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
from common_server_worker import DLROBOT_HTTP_CODE, TTimeouts, TYandexCloud, DLROBOT_HEADER_KEYS
from robots.common.primitives import convert_timeout_to_seconds, check_internet
import ipaddress
from remote_call import TRemoteDlrobotCall
from robots.common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from robots.dlrobot.scripts.cloud.smart_parser_cache_client import TSmartParserCacheClient
import shutil

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
    parser.add_argument("--tries-count", dest='tries_count', required=False, default=2, type=int)
    parser.add_argument("--read-previous-results", dest='read_previous_results', default=False, action='store_true',
                        required=False, help="read file dlrobot_results.dat and exclude succeeded tasks from the input tasks")

    parser.add_argument("--central-heart-rate", dest='central_heart_rate', required=False, default='20s')
    parser.add_argument("--dlrobot-project-timeout", dest='dlrobot_project_timeout',
                         required=False, default=TTimeouts.OVERALL_HARD_TIMEOUT_IN_CENTRAL)
    parser.add_argument("--check-yandex-cloud", dest='check_yandex_cloud', default=False, action='store_true',
                        required=False, help="check yandex cloud health and restart workstations")
    parser.add_argument("--skip-worker-check", dest='skip_worker_check', default=False, action='store_true',
                        required=False, help="skip checking that this tast was given to this worker")
    parser.add_argument("--enable-ip-checking", dest='enable_ip_checking', default=False, action='store_true',
                        required=False)
    parser.add_argument("--pdf-conversion-queue-limit", dest='pdf_conversion_queue_limit', type=int,
                        default=100 * 2 ** 20, help="max sum size of al pdf files that are in pdf conversion queue",
                        required=False)
    parser.add_argument("--crawl-epoch-id", dest="crawl_epoch_id", default="1", type=int)
    parser.add_argument("--disable-smart-parser-cache", dest="enable_smart_parser",
                        default=True, action="store_false", required=False)

    args = parser.parse_args()
    args.central_heart_rate = convert_timeout_to_seconds(args.central_heart_rate)
    args.dlrobot_project_timeout = convert_timeout_to_seconds(args.dlrobot_project_timeout)
    if args.server_address is None:
        args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
    if args.check_yandex_cloud:
        assert TYandexCloud.get_yc() is not None

    return args


class TDlrobotHTTPServer(http.server.HTTPServer):

    def initialize_tasks(self):
        self.dlrobot_remote_calls.clear()
        self.worker_2_running_tasks.clear()
        self.input_files = list(x for x in os.listdir(self.args.input_folder) if x.endswith('.txt'))
        if not os.path.exists(self.args.result_folder):
            os.makedirs(self.args.result_folder)
        if args.read_previous_results:
            self.read_prev_dlrobot_remote_calls()
        logger.debug("there are {} dlrobot projects to process".format(len(self.input_files)))
        self.worker_2_running_tasks.clear()

    def __init__(self, args, logger):
        self.timeout = 60 * 10
        self.conversion_client = TDocConversionClient(logger)
        self.args = args
        self.logger = logger
        self.dlrobot_remote_calls = defaultdict(list)
        self.input_files = list()
        self.worker_2_running_tasks = defaultdict(list)
        self.initialize_tasks()
        self.cloud_id_to_worker_ip = dict()
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, port))
        super().__init__((host, int(port)), TDlrobotRequestHandler)
        self.last_service_action_time_stamp = time.time()
        self.smart_parser_cache_client = None
        if self.args.enable_smart_parser:
            self.smart_parser_cache_client = TSmartParserCacheClient(self.logger)
        self.crawl_epoch_id = self.args.crawl_epoch_id

        if self.args.enable_ip_checking:
            self.permitted_hosts = set(str(x) for x in ipaddress.ip_network('192.168.100.0/24').hosts())
            self.permitted_hosts.add('127.0.0.1')
            self.permitted_hosts.add('95.165.96.61') # disclosures.ru

    def verify_request(self, request, client_address):
        if self.args.enable_ip_checking:
            (ip, dummy) = client_address
            if ip not in self.permitted_hosts:
                return False
        return True

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
            outp.write(json.dumps(remote_call.write_to_json()) + "\n")
        self.dlrobot_remote_calls[remote_call.project_file].append(remote_call)
        if remote_call.exit_code != 0:
            max_tries_count = args.tries_count
            tries_count = len(self.dlrobot_remote_calls[remote_call.project_file])
            if remote_call.result_folder is None and tries_count == max_tries_count:
                # if the last result was not obtained, may be,
                # worker is down, so the problem is not in the task but in the worker
                # so give this task one more chance
                max_tries_count += 1
                self.logger.debug("increase max_tries_count for {} to {}".format(remote_call.project_file, max_tries_count))

            if tries_count < max_tries_count:
                self.input_files.append(remote_call.project_file)
                self.logger.debug("register retry for {}".format(remote_call.project_file))

    def input_tasks_exist(self):
        with os.scandir(self.args.input_folder) as it:
            for entry in it:
                if entry.name.endswith(".txt"):
                    return True
        return False

    def can_start_new_epoch(self):
        if not self.input_tasks_exist():
            return False
        if self.get_running_jobs_count() > 0:
            return False
        return True

    def start_new_epoch(self):
        archive_filename = "{}.{}".format( self.get_dlrobot_remote_calls_filename(), self.crawl_epoch_id)
        if os.path.exists(archive_filename):
            self.logger.error("cannot create file {}, already exists".format(archive_filename))
            raise Exception("bad crawl epoch id")
        shutil.move(self.get_dlrobot_remote_calls_filename(), archive_filename)
        self.crawl_epoch_id += 1
        self.logger.error("start new epoch {}".format(self.crawl_epoch_id))
        self.initialize_tasks()

    def read_prev_dlrobot_remote_calls(self):
        if os.path.exists(self.get_dlrobot_remote_calls_filename()):
            self.logger.debug("read {}".format(self.get_dlrobot_remote_calls_filename()))
            calls = TRemoteDlrobotCall.read_remote_calls_from_file(self.get_dlrobot_remote_calls_filename())
            for remote_call in calls:
                self.dlrobot_remote_calls[remote_call.project_file].append(remote_call)
                if remote_call.exit_code == 0 and remote_call.project_file in self.input_files:
                    self.logger.debug("delete {}, since it is already processed".format(remote_call.project_file))
                    self.input_files.remove(remote_call.project_file)

    def get_running_jobs_count(self):
        return sum(len(w) for w in self.worker_2_running_tasks.values())

    def get_processed_jobs_count(self):
        return sum(len(w) for w in self.dlrobot_remote_calls.values())

    def conversion_server_queue_is_short(self):
        input_queue_size = self.conversion_client.get_pending_all_file_size()
        self.logger.debug("conversion pdf input_queue_size={}".format(input_queue_size))
        return input_queue_size < self.args.pdf_conversion_queue_limit

    def get_new_job_task(self, worker_host_name, worker_ip):
        project_file = self.input_files.pop()
        self.logger.info("start job: {} on {} (host name={}), left jobs: {}, running jobs: {}".format(
                project_file, worker_ip, worker_host_name, len(self.input_files), self.get_running_jobs_count()))
        res = TRemoteDlrobotCall(worker_ip, project_file)
        res.worker_host_name = worker_host_name
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
        return output_folder

    def pop_project_from_running_tasks (self, worker_ip, project_file):
        if worker_ip not in self.worker_2_running_tasks:
            raise Exception("{} is missing in the worker table".format(worker_ip))
        worker_running_tasks = self.worker_2_running_tasks[worker_ip]
        for i in range(len(worker_running_tasks)):
            if worker_running_tasks[i].project_file == project_file:
                return worker_running_tasks.pop(i)
        raise Exception("{} is missing in the worker {} task table".format(project_file, worker_ip))

    def send_declaraion_files_to_smart_parser(self, result_folder):
        doc_folder = os.path.join(result_folder, "result")
        if os.path.exists(doc_folder):
            for website in os.listdir(doc_folder):
                website_folder = os.path.join(doc_folder, website)
                for doc in os.listdir(website_folder):
                    _, extension = os.path.splitext(doc)
                    if extension in ACCEPTED_DOCUMENT_EXTENSIONS:
                        self.smart_parser_cache_client.send_file(os.path.join(website_folder, doc))

    def register_task_result(self, worker_host_name, worker_ip, project_file, exit_code, result_archive):
        if args.skip_worker_check:
            remote_call = TRemoteDlrobotCall(worker_ip, project_file)
        else:
            remote_call = self.pop_project_from_running_tasks(worker_ip, project_file)
        remote_call.worker_host_name = worker_host_name
        remote_call.exit_code = exit_code
        remote_call.end_time = int(time.time())
        remote_call.result_folder = self.untar_file(project_file, result_archive)
        remote_call.calc_project_stats()
        if self.args.enable_smart_parser:
            self.send_declaraion_files_to_smart_parser(remote_call.result_folder)
        self.save_dlrobot_remote_call(remote_call)

        self.logger.debug("got exitcode {} for task result {} from worker {}".format(
            exit_code, project_file, worker_ip))

    def forget_old_remote_processes(self, current_time):
        for running_procs in self.worker_2_running_tasks.values():
            for i in range(len(running_procs) - 1, -1, -1):
                rc = running_procs[i]
                if current_time - rc.start_time > args.dlrobot_project_timeout:
                    self.logger.debug("task {} on worker {} takes {} seconds, probably it failed, stop waiting for a result".format(
                        rc.project_file, rc.worker_ip, current_time - rc.start_time
                    ))
                    running_procs.pop(i)
                    rc.exit_code = 126
                    self.save_dlrobot_remote_call(rc)

    def forget_remote_processes_for_yandex_worker(self, cloud_id, current_time):
        worker_ip = self.cloud_id_to_worker_ip.get(cloud_id)
        if worker_ip is None and len(self.cloud_id_to_worker_ip) > 0:
            self.logger.info("I do not remember ip for cloud_id {}, cannot delete processes".format(cloud_id))
            return

        running_procs = self.worker_2_running_tasks.get(worker_ip, list())
        for i in range(len(running_procs) - 1, -1, -1):
            rc = running_procs[i]
            self.logger.debug(
                "forget task {} on worker {} since the workstation was stopped".format(
                    rc.project_file, rc.worker_ip
                ))
            running_procs.pop(i)
            rc.exit_code = 125
            self.save_dlrobot_remote_call(rc)
        if cloud_id in self.cloud_id_to_worker_ip:
            del self.cloud_id_to_worker_ip[cloud_id]

    def check_yandex_cloud(self):
        if not self.args.check_yandex_cloud:
            return None
        try:
            if not check_internet():
                self.logger.error("cannot connect to google dns, probably internet is down")
                return None
            current_time = time.time()
            for m in TYandexCloud.list_instances():
                cloud_id = m['id']
                if m['status'] == 'STOPPED':
                    self.forget_remote_processes_for_yandex_worker(cloud_id, current_time)
                    self.logger.info("start yandex cloud worker {}".format(cloud_id))
                    TYandexCloud.start_yandex_cloud_worker(cloud_id)
                elif m['status'] == "RUNNING":
                    worker_ip = TYandexCloud.get_worker_ip(m)
                    if self.args.enable_ip_checking:
                        self.permitted_hosts.add(worker_ip)
                    self.cloud_id_to_worker_ip[cloud_id] = worker_ip
        except Exception as exp:
            self.logger.error(exp)

    def service_actions(self):
        current_time = time.time()
        if current_time - self.last_service_action_time_stamp >= args.central_heart_rate:
            self.last_service_action_time_stamp = current_time
            self.forget_old_remote_processes(current_time)
            self.check_yandex_cloud()

    def get_stats(self):
        workers = dict((k, list(r.write_to_json() for r in v))
                            for (k, v) in self.worker_2_running_tasks.items())

        return {
            'running_count': self.get_running_jobs_count(),
            'input_tasks': len(self.input_files),
            'processed_tasks': self.get_processed_jobs_count(),
            'worker_2_running_tasks':  workers
        }



HTTP_SERVER = None


class TDlrobotRequestHandler(http.server.BaseHTTPRequestHandler):

    timeout = 10*60

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

    def process_special_commands(self):
        global HTTP_SERVER
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong\n")
            return True
        if self.path == "/stats":
            self.send_response(200)
            self.end_headers()
            stats = json.dumps(HTTP_SERVER.get_stats()) + "\n"
            self.wfile.write(stats.encode('utf8'))
            return True
        return False

    def do_GET(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST, log_error=True):
            if log_error:
                HTTP_SERVER.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)
        global HTTP_SERVER
        query_components = dict()
        if not self.parse_cgi(query_components):
            send_error('bad request', log_error=False)
            return

        try:
            if self.process_special_commands():
                return
        except Exception as exp:
            HTTP_SERVER.logger.error(exp)
            return

        dummy_code = query_components.get('authorization_code', None)
        if not dummy_code:
            send_error('No authorization_code provided', log_error=False)
            return

        if len(HTTP_SERVER.input_files) == 0 and HTTP_SERVER.can_start_new_epoch():
            HTTP_SERVER.start_new_epoch()

        if len(HTTP_SERVER.input_files) == 0:
            send_error("no more jobs", DLROBOT_HTTP_CODE.NO_MORE_JOBS)
            return

        worker_host_name = self.headers.get(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME)
        if worker_host_name is None:
            send_error('cannot find header {}'.format(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME))
            return

        if not HTTP_SERVER.conversion_server_queue_is_short():
            send_error("pdf conversion server is too busy", DLROBOT_HTTP_CODE.TOO_BUSY)
            return

        worker_ip = self.client_address[0]
        try:
            project_file = HTTP_SERVER.get_new_job_task(worker_host_name, worker_ip)
        except Exception as exp:
            send_error(str(exp))
            return

        self.send_response(200)
        self.send_header(DLROBOT_HEADER_KEYS.PROJECT_FILE,  project_file)
        self.end_headers()

        file_path = os.path.join(HTTP_SERVER.args.input_folder, project_file)
        with open(file_path, 'rb') as fh:
            self.wfile.write(fh.read())

    def do_PUT(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST):
            HTTP_SERVER.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)

        global HTTP_SERVER
        if self.path is None:
            send_error("no file specified")
            return

        _, file_extension = os.path.splitext(os.path.basename(self.path))

        file_length = self.headers.get('Content-Length')
        if file_length is None or not file_length.isdigit():
            send_error('cannot find header  Content-Length')
            return
        file_length = int(file_length)

        project_file = self.headers.get('dlrobot_project_file_name')
        if project_file is None:
            send_error('cannot find header "dlrobot_project_file_name"')
            return

        exitcode = self.headers.get(DLROBOT_HEADER_KEYS.EXIT_CODE)
        if exitcode is None or not exitcode.isdigit():
            send_error('missing exitcode or bad exit code')
            return

        worker_host_name = self.headers.get(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME)
        if worker_host_name is None:
            send_error('cannot find header "{]'.format(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME))
            return

        worker_ip = self.client_address[0]
        HTTP_SERVER.logger.debug(
            "start reading file {} file size {} from {}".format(project_file, file_length, worker_ip))

        try:
            archive_file_bytes = self.rfile.read(file_length)
        except Exception as exp:
            send_error('file reading failed: {}'.format(str(exp)))
            return

        try:
            HTTP_SERVER.register_task_result(worker_host_name, worker_ip, project_file, int(exitcode),  archive_file_bytes)
        except Exception as exp:
            send_error('register_task_result failed: {}'.format(str(exp)))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging(args.log_file_name)
    HTTP_SERVER = TDlrobotHTTPServer(args, logger)
    if not HTTP_SERVER.input_tasks_exist():
        logger.error("no input tasks found")
        sys.exit(1)

    HTTP_SERVER.check_yandex_cloud() # to get worker ips
    try:
        HTTP_SERVER.serve_forever()
    except KeyboardInterrupt:
        logger.info("ctrl+c received")
        sys.exit(1)
    except Exception as exp:
        sys.stderr.write("general exception: {}\n".format(exp))
        logger.error("general exception: {}".format(exp))
        sys.exit(1)

