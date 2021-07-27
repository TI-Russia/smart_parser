from ConvStorage.conversion_client import TDocConversionClient
from dlrobot_server.common_server_worker import DLROBOT_HTTP_CODE, TTimeouts, TYandexCloud, DLROBOT_HEADER_KEYS, PITSTOP_FILE
from common.primitives import convert_timeout_to_seconds, check_internet, TUrlUtf8Encode
from common.content_types import ACCEPTED_DOCUMENT_EXTENSIONS
from smart_parser_http.smart_parser_client import TSmartParserCacheClient
from web_site_db.remote_call import TRemoteDlrobotCall, TRemoteDlrobotCallList
from source_doc_http.source_doc_client import TSourceDocClient
from web_site_db.web_site_status import TWebSiteReachStatus
from web_site_db.web_sites import TDeclarationWebSiteList, TDeclarationRounds
from web_site_db.robot_project import TRobotProject
from common.logging_wrapper import setup_logging

import argparse
import re
import sys
import os
from collections import defaultdict
import time
import json
import urllib
import http.server
import io, gzip, tarfile
import ipaddress
import telegram_send


class TDlrobotHTTPServer(http.server.HTTPServer):
    max_continuous_failures_count = 7

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable DLROBOT_CENTRAL_SERVER_ADDRESS")

        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="dlrobot_central.log")
        parser.add_argument("--input-task-list", dest='input_task_list', required=False,
                            default=TDeclarationWebSiteList.default_input_task_list_path)
        parser.add_argument("--remote-calls-file", dest='remote_calls_file', default=None)
        parser.add_argument("--result-folder", dest='result_folder', required=True)
        parser.add_argument("--tries-count", dest='tries_count', required=False, default=2, type=int)
        parser.add_argument("--central-heart-rate", dest='central_heart_rate', required=False, default='60s')
        parser.add_argument("--dlrobot-crawling-timeout", dest='dlrobot_crawling_timeout',
                            required=False, default=TTimeouts.MAIN_CRAWLING_TIMEOUT)
        parser.add_argument("--check-yandex-cloud", dest='check_yandex_cloud', default=False, action='store_true',
                            required=False, help="check yandex cloud health and restart workstations")
        parser.add_argument("--skip-worker-check", dest='skip_worker_check', default=False, action='store_true',
                            required=False, help="skip checking that this tast was given to this worker")
        parser.add_argument("--enable-ip-checking", dest='enable_ip_checking', default=False, action='store_true',
                            required=False)
        parser.add_argument("--disable-smart-parser-server", dest="enable_smart_parser",
                            default=True, action="store_false", required=False)
        parser.add_argument("--disable-source-doc-server", dest="enable_source_doc_server",
                            default=True, action="store_false", required=False)
        parser.add_argument("--disable-search-engines", dest="enable_search_engines",
                            default=True, action="store_false", required=False)
        parser.add_argument("--disable-telegram", dest="enable_telegram",
                            default=True,  required=False, action="store_false")
        parser.add_argument("--disable-pdf-conversion-server-checking", dest="pdf_conversion_server_checking",
                            default=True,  required=False, action="store_false")
        parser.add_argument("--web-site-regexp", dest="web_site_regexp", required=False)
        parser.add_argument("--round-file", dest="round_file", default=TDeclarationRounds.default_dlrobot_round_path)

        args = parser.parse_args(arg_list)
        args.central_heart_rate = convert_timeout_to_seconds(args.central_heart_rate)
        args.dlrobot_crawling_timeout = convert_timeout_to_seconds(args.dlrobot_crawling_timeout)
        if args.server_address is None:
            args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
        if args.check_yandex_cloud:
            assert TYandexCloud.get_yc() is not None

        return args

    def __init__(self, args):
        self.register_task_result_error_count = 0
        self.logger = setup_logging(log_file_name=args.log_file_name, append_mode=True)
        self.conversion_client = TDocConversionClient(TDocConversionClient.parse_args([]), self.logger)
        self.args = args
        rounds = TDeclarationRounds(args.round_file)
        self.dlrobot_remote_calls = TRemoteDlrobotCallList(logger=self.logger, file_name=args.remote_calls_file,
                                                           min_start_time_stamp=rounds.start_time_stamp)
        self.worker_2_running_tasks = defaultdict(list)
        self.worker_2_continuous_failures_count = defaultdict(int)
        self.web_sites_db = TDeclarationWebSiteList(self.logger, self.args.input_task_list).load_from_disk()
        if not os.path.exists(self.args.result_folder):
            os.makedirs(self.args.result_folder)
        self.web_sites_to_process = self.find_projects_to_process()
        self.cloud_id_to_worker_ip = dict()
        self.last_remote_call = None  # for testing
        host, port = self.args.server_address.split(":")
        self.logger.debug("start server on {}:{}".format(host, port))
        super().__init__((host, int(port)), TDlrobotRequestHandler)
        self.last_service_action_time_stamp = time.time()
        self.service_action_count = 0
        self.smart_parser_server_client = None
        if self.args.enable_smart_parser:
            sp_args = TSmartParserCacheClient.parse_args([])
            self.smart_parser_server_client = TSmartParserCacheClient(sp_args, self.logger)
        self.source_doc_client = None
        if self.args.enable_source_doc_server:
            sp_args = TSourceDocClient.parse_args([])
            self.source_doc_client = TSourceDocClient(sp_args, self.logger)
        self.stop_process = False
        if self.args.enable_ip_checking:
            self.permitted_hosts = set(str(x) for x in ipaddress.ip_network('192.168.100.0/24').hosts())
            self.permitted_hosts.add('127.0.0.1')
            self.permitted_hosts.add('95.165.96.61') # disclosures.ru
        self.logger.debug("init complete")
        self.send_to_telegram("start dlrobot central with {} tasks".format(len(self.web_sites_to_process)))

    def send_to_telegram(self, message):
        if self.args.enable_telegram:
            self.logger.debug("send to telegram: {}".format(message))
            telegram_send.send(messages=[message])

    def stop_server(self):
        self.server_close()
        self.shutdown()

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

    def have_tasks(self):
        return len(self.web_sites_to_process) > 0 and not self.stop_process

    def project_is_to_process(self, project_file):
        interactions = self.dlrobot_remote_calls.get_interactions(project_file)
        if sum(1 for i in interactions if i.task_was_successful()) > 0:
            return False
        tries_count = self.args.tries_count
        if sum(1 for i in interactions if not i.task_ended()) > 0:
            # if the last result was not obtained, may be,
            # worker is down, so the problem is not in the task but in the worker
            # so give this task one more chance
            tries_count += 1
            self.logger.debug("increase max_tries_count for {} to {}".format(project_file, tries_count))
        return len(interactions) < tries_count

    def save_dlrobot_remote_call(self, remote_call: TRemoteDlrobotCall):
        self.dlrobot_remote_calls.add_dlrobot_remote_call(remote_call)
        if not remote_call.task_was_successful():
            if self.project_is_to_process(remote_call.project_file):
                self.web_sites_to_process.append(remote_call.web_site)
                self.logger.debug("register retry for {}".format(remote_call.web_site))

    def find_projects_to_process(self):
        web_sites_to_process = list()
        self.logger.info("filter web sites")
        for web_site, web_site_info in self.web_sites_db.web_sites.items():
            if self.args.web_site_regexp is not None:
                if re.match(self.args.web_site_regexp, web_site) is None:
                    continue
            if TWebSiteReachStatus.can_communicate(web_site_info.reach_status):
                project_file = TRemoteDlrobotCall.web_site_to_project_file(web_site)
                if self.project_is_to_process(project_file):
                    web_sites_to_process.append(web_site)

        self.logger.info("there are {} sites in the input queue".format(len(web_sites_to_process)))
        web_sites_to_process.sort(key=(lambda x: self.dlrobot_remote_calls.last_interaction[x]))

        with open("web_sites_to_process_debug.txt", "w") as out:
            for w in web_sites_to_process:
                out.write(w + "\n")
        return web_sites_to_process

    def get_running_jobs_count(self):
        return sum(len(w) for w in self.worker_2_running_tasks.values())

    def get_processed_jobs_count(self):
        return len(list(self.dlrobot_remote_calls.get_all_calls()))

    def get_new_project_to_process(self, worker_host_name, worker_ip):
        site_url = self.web_sites_to_process.pop(0)
        project_file = TRemoteDlrobotCall.web_site_to_project_file(site_url)
        self.logger.info("start job: {} on {} (host name={}), left jobs: {}, running jobs: {}".format(
                project_file, worker_ip, worker_host_name, len(self.web_sites_to_process), self.get_running_jobs_count()))
        remote_call = TRemoteDlrobotCall(worker_ip=worker_ip, project_file=project_file, web_site=site_url)
        remote_call.worker_host_name = worker_host_name
        remote_call.crawling_timeout = self.args.dlrobot_crawling_timeout
        web_site_passport = self.web_sites_db.get_web_site(site_url)
        enable_selenium = True
        regional_main_pages = list()
        if web_site_passport is None:
            self.logger.error("{} is not registered in the web site db, no office information is available for the site")
        else:
            remote_call.crawling_timeout = int(remote_call.crawling_timeout * web_site_passport.dlrobot_max_time_coeff)
            if web_site_passport.regional_main_pages is not None:
                regional_main_pages = list(web_site_passport.regional_main_pages.keys())
            if web_site_passport.disable_selenium:
                enable_selenium = False
        project_content_str = TRobotProject.create_project_str(site_url,
                                                               regional_main_pages,
                                                               not self.args.enable_search_engines,
                                                               not enable_selenium)
        self.worker_2_running_tasks[worker_ip].append(remote_call)
        return remote_call, project_content_str.encode("utf8")

    def untar_file(self, project_file, result_archive):
        base_folder, _ = os.path.splitext(project_file)
        output_folder = os.path.join(self.args.result_folder, base_folder) + ".{}".format(int(time.time()))
        compressed_file = io.BytesIO(result_archive)
        decompressed_file = gzip.GzipFile(fileobj=compressed_file)
        tar = tarfile.open(fileobj=decompressed_file)
        tar.extractall(output_folder)
        return output_folder

    def pop_project_from_running_tasks(self, worker_ip, project_file):
        if worker_ip not in self.worker_2_running_tasks:
            raise Exception("{} is missing in the worker table".format(worker_ip))
        worker_running_tasks = self.worker_2_running_tasks[worker_ip]
        for i in range(len(worker_running_tasks)):
            if worker_running_tasks[i].project_file == project_file:
                return worker_running_tasks.pop(i)
        raise Exception("{} is missing in the worker {} task table".format(project_file, worker_ip))

    def send_declaraion_files_to_other_servers(self, dlrobot_project_folder):
        doc_folder = os.path.join(dlrobot_project_folder, "result")
        if os.path.exists(doc_folder):
            for website in os.listdir(doc_folder):
                website_folder = os.path.join(doc_folder, website)
                for doc in os.listdir(website_folder):
                    _, extension = os.path.splitext(doc)
                    if extension in ACCEPTED_DOCUMENT_EXTENSIONS:
                        file_path = os.path.join(website_folder, doc)
                        if self.smart_parser_server_client is not None:
                            self.logger.debug("send {} to smart_parser_server".format(doc))
                            self.smart_parser_server_client.send_file(file_path)
                        if self.source_doc_client is not None:
                            self.logger.debug("send {} to source_doc_server".format(doc))
                            self.source_doc_client.send_file(file_path)

    def worker_is_banned(self, worker_ip, host_name):
        return self.worker_2_continuous_failures_count[(worker_ip, host_name)] > \
                        TDlrobotHTTPServer.max_continuous_failures_count

    def update_worker_info(self, worker_host_name, worker_ip, exit_code):
        key = (worker_ip, worker_host_name)
        if exit_code == 0:
            self.worker_2_continuous_failures_count[key] = 0
        else:
            self.worker_2_continuous_failures_count[key] += 1
            if self.worker_is_banned(worker_ip, worker_host_name):
                self.send_to_telegram("too many dlrobot errors from ip {}, hostname={}, the host is banned, "
                                      "you have to restart dlrobot_central to unban it".format(worker_ip,
                                                                                               worker_host_name))

    def register_task_result(self, worker_host_name, worker_ip, project_file, exit_code, result_archive):
        if self.args.skip_worker_check:
            remote_call = TRemoteDlrobotCall(worker_ip, project_file)
        else:
            try:
                remote_call = self.pop_project_from_running_tasks(worker_ip, project_file)
            except:
                if ipaddress.ip_address(worker_ip).is_private:
                    self.logger.debug("try to get a result {} from a local ip {}, though this task was not dispatched".format(
                        project_file, worker_ip))
                    remote_call = TRemoteDlrobotCall(worker_ip, project_file)
                else:
                    raise

        self.update_worker_info(worker_host_name, worker_ip, exit_code)

        remote_call.worker_host_name = worker_host_name
        remote_call.exit_code = exit_code
        remote_call.end_time = int(time.time())
        project_folder = self.untar_file(project_file, result_archive)
        remote_call.calc_project_stats(self.logger, project_folder)
        if not TWebSiteReachStatus.can_communicate(remote_call.reach_status):
            remote_call.exit_code = -1
        self.send_declaraion_files_to_other_servers(project_folder)
        self.save_dlrobot_remote_call(remote_call)
        self.last_remote_call = remote_call
        self.logger.debug("got exitcode {} for task result {} from worker {} (host_name = {})".format(
            exit_code, project_file, worker_ip, worker_host_name))

    def forget_old_remote_processes(self, current_time):
        for running_procs in self.worker_2_running_tasks.values():
            for i in range(len(running_procs) - 1, -1, -1):
                remote_call = running_procs[i]
                elapsed_seconds = current_time - remote_call.start_time
                if elapsed_seconds > TTimeouts.get_kill_timeout_in_central(remote_call.crawling_timeout):
                    self.logger.debug("task {} on worker {}(host={}) takes {} seconds, probably it failed, stop waiting for a result".format(
                        remote_call.web_site, remote_call.worker_ip, remote_call.worker_host_name,
                        elapsed_seconds
                    ))
                    running_procs.pop(i)
                    remote_call.exit_code = 126
                    self.save_dlrobot_remote_call(remote_call)

    def forget_remote_processes_for_yandex_worker(self, cloud_id):
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
            for m in TYandexCloud.list_instances():
                cloud_id = m['id']
                if m['status'] == 'STOPPED':
                    self.forget_remote_processes_for_yandex_worker(cloud_id)
                    self.logger.info("start yandex cloud worker {}".format(cloud_id))
                    TYandexCloud.start_yandex_cloud_worker(cloud_id)
                elif m['status'] == "RUNNING":
                    worker_ip = TYandexCloud.get_worker_ip(m)
                    if self.args.enable_ip_checking:
                        self.permitted_hosts.add(worker_ip)
                    self.cloud_id_to_worker_ip[cloud_id] = worker_ip
        except Exception as exp:
            self.logger.error(exp)

    def check_pdf_conversion_server(self):
        if not self.args.pdf_conversion_server_checking:
            return True
        return not self.conversion_client.server_is_too_busy()

    def service_actions(self):
        current_time = time.time()
        if current_time - self.last_service_action_time_stamp >= self.args.central_heart_rate:
            self.service_action_count += 1
            if self.service_action_count % 10 == 0:
                self.logger.debug('alive')
            self.last_service_action_time_stamp = current_time
            if os.path.exists(PITSTOP_FILE):
                self.stop_process = True
                self.logger.debug("stop sending tasks, exit for a pit stop after all tasks complete")
                os.unlink(PITSTOP_FILE)
            if self.stop_process and self.get_running_jobs_count() == 0:
                self.logger.debug("exit via exception")
                raise Exception("exit for pit stop")
            try:
                self.forget_old_remote_processes(current_time)
            except Exception as exp:
                self.logger.error(exp)
            self.check_yandex_cloud()
            if not self.check_pdf_conversion_server():
                self.logger.debug("stop sending tasks, because conversion pdf queue length is {}".format(
                    self.conversion_client.last_pdf_conversion_queue_length))

    def get_stats(self):
        workers = dict((k, list(r.write_to_json() for r in v))
                            for (k, v) in self.worker_2_running_tasks.items())
        stats = {
            'running_count': self.get_running_jobs_count(),
            'input_tasks': len(self.web_sites_to_process),
            'processed_tasks': self.get_processed_jobs_count(),
            'worker_2_running_tasks':  workers,
            'last_service_action_time_stamp': self.last_service_action_time_stamp,
            'central_heart_rate': self.args.central_heart_rate,
            'register_task_result_error_count': self.register_task_result_error_count
        }
        if self.stop_process:
            stats['stop_process'] = True
        return stats


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
        if self.path == "/ping":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong\n")
            return True
        if self.path == "/stats":
            self.send_response(200)
            self.end_headers()
            stats = json.dumps(self.server.get_stats()) + "\n"
            self.wfile.write(stats.encode('utf8'))
            return True
        if self.path == "/unban-all":
            self.worker_2_continuous_failures_count.clear()
            self.server.logger.error(exp)
            self.send_response(200)
            self.end_headers()
            return True
        return False

    def do_GET(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST, log_error=True):
            if log_error:
                self.server.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)
        query_components = dict()
        if not self.parse_cgi(query_components):
            send_error('bad request', log_error=False)
            return

        try:
            if self.process_special_commands():
                return
        except Exception as exp:
            self.server.logger.error(exp)
            return

        dummy_code = query_components.get('authorization_code', None)
        if not dummy_code:
            send_error('No authorization_code provided', log_error=False)
            return

        if not self.server.have_tasks():
            send_error("no more jobs", DLROBOT_HTTP_CODE.NO_MORE_JOBS)
            return

        worker_host_name = self.headers.get(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME)
        if worker_host_name is None:
            send_error('cannot find header {}'.format(DLROBOT_HEADER_KEYS.WORKER_HOST_NAME))
            return

        if not self.server.check_pdf_conversion_server():
            send_error("pdf conversion server is too busy", DLROBOT_HTTP_CODE.TOO_BUSY)
            return
    
        worker_ip = self.client_address[0]

        if self.server.worker_is_banned(worker_ip, worker_host_name):
            error_msg = "too many dlrobot errors from ip {} hostname {}".format(worker_ip, worker_host_name)
            send_error(error_msg, DLROBOT_HTTP_CODE.TOO_BUSY)
            return

        try:
            remote_call, project_content = self.server.get_new_project_to_process(worker_host_name, worker_ip)
        except Exception as exp:
            self.server.error.logger("Cannot send project, exception = {}".format(exp))
            send_error(str(exp))
            return

        self.send_response(200)
        self.send_header(DLROBOT_HEADER_KEYS.PROJECT_FILE, TUrlUtf8Encode.to_idna(remote_call.project_file))
        self.send_header(DLROBOT_HEADER_KEYS.CRAWLING_TIMEOUT, remote_call.crawling_timeout)
        self.end_headers()
        self.wfile.write(project_content)

    def do_PUT(self):
        def send_error(message, http_code=http.HTTPStatus.BAD_REQUEST):
            self.server.logger.error(message)
            http.server.SimpleHTTPRequestHandler.send_error(self, http_code, message)

        if self.path is None:
            send_error("no file specified")
            return

        file_length = self.headers.get('Content-Length')
        if file_length is None or not file_length.isdigit():
            send_error('cannot find header  Content-Length')
            return
        file_length = int(file_length)

        project_file = TUrlUtf8Encode.from_idna(self.headers.get(DLROBOT_HEADER_KEYS.PROJECT_FILE))
        if project_file is None:
            send_error('cannot find header "{}"'.format(DLROBOT_HEADER_KEYS.PROJECT_FILE))
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
        self.server.logger.debug(
            "start reading file {} file size {} from {}".format(project_file, file_length, worker_ip))

        try:
            archive_file_bytes = self.rfile.read(file_length)
        except Exception as exp:
            send_error('file reading failed: {}'.format(str(exp)))
            return

        try:
            self.server.register_task_result(worker_host_name, worker_ip, project_file, int(exitcode),  archive_file_bytes)
        except Exception as exp:
            send_error('register_task_result failed: {}'.format(str(exp)))
            self.server.register_task_result_error_count += 1
            if self.server.register_task_result_error_count % 10 == 0:
                self.server.send_to_telegram("dlrobot_central: register_task_result_error_count: {}".format(
                    self.server.register_task_result_error_count))
            return

        self.send_response(http.HTTPStatus.CREATED)
        self.end_headers()


if __name__ == "__main__":
    args = TDlrobotHTTPServer.parse_args(sys.argv[1:])
    server = TDlrobotHTTPServer(args)

    server.check_yandex_cloud() # to get worker ips
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.logger.info("ctrl+c received")
        sys.exit(1)
    except Exception as exp:
        server.logger.error("general exception: {}".format(exp))
        sys.exit(1)

