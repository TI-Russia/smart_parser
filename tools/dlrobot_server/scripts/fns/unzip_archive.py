from dlrobot_server.common_server_worker import DLROBOT_HEADER_KEYS
from common.archives import TDearchiver
from common.robot_project import TRobotProject
from common.robot_web_site import TWebSiteReachStatus
from common.export_files import TExportFile
from common.logging_wrapper import setup_logging

import argparse
import os
import sys
import time
import http.server
import shutil
import tarfile
import platform
from bs4 import BeautifulSoup

#see add_fns_json_to_html.sh to know how to use it

class TUnzipper:
    def __init__(self, args):
        self.args = args
        self.working = True
        self.logger = setup_logging(log_file_name=self.args.log_file_name)
        self.setup_environment()

    @staticmethod
    def parse_args(arg_list):
        parser = argparse.ArgumentParser()
        parser.add_argument("--archive", dest='archive_path', required=True)
        parser.add_argument("--server-address", dest='server_address', default=None,
                            help="by default read it from environment variable DLROBOT_CENTRAL_SERVER_ADDRESS")
        parser.add_argument("--log-file-name", dest='log_file_name', required=False, default="unzip_archive.log")
        parser.add_argument("--http-put-timeout", dest='http_put_timeout', required=False, type=int, default=60 * 10)
        parser.add_argument("--web-domain", dest='web_domain', required=True)
        parser.add_argument("--wait-after-each-doc", dest='wait_after_each_doc', type=int, default=1)
        args = parser.parse_args(arg_list)
        return args

    def get_url_from_meta_tag(self, html_path, default=None):
        with open(html_path, "rb") as inp:
            soup = BeautifulSoup(inp.read(), "html.parser")
            for meta_tag in soup.find_all("meta"):
                if meta_tag.attrs.get('name') == 'smartparser_url':
                    return meta_tag.attrs.get('content')
        return default

    def send_files_to_central(self, files):
        project_folder = self.args.web_domain
        shutil.rmtree(project_folder, ignore_errors=True)
        os.mkdir(project_folder)
        os.chdir(project_folder)

        robot_project_path = os.path.join(self.args.web_domain + ".txt")
        TRobotProject.create_project(self.args.web_domain, robot_project_path)
        with TRobotProject(self.logger, robot_project_path, [], None, enable_selenium=False,
                           enable_search_engine=False) as project:
            project.add_office(self.args.web_domain)
            project.offices[0].reach_status = TWebSiteReachStatus.normal
            export_env = project.offices[0].export_env
            for file_name in files:
                web_domain = self.args.web_domain
                if file_name.endswith('.html'):
                    web_domain = self.get_url_from_meta_tag(file_name, web_domain)
                export_path = os.path.join("result", web_domain, os.path.basename(file_name))
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                shutil.move(file_name, export_path)
                export_file = TExportFile(url=self.args.web_domain, export_path=export_path)
                export_env.exported_files.append(export_file)
            project.write_project()
        os.chdir("../../..")

        headers = {
            DLROBOT_HEADER_KEYS.EXIT_CODE: 0,
            DLROBOT_HEADER_KEYS.PROJECT_FILE: os.path.basename(robot_project_path),
            DLROBOT_HEADER_KEYS.WORKER_HOST_NAME: platform.node(),
            "Content-Type": "application/binary"
        }
        self.logger.debug("send results back for {}".format(robot_project_path))
        dlrobot_results_file_name = os.path.basename(robot_project_path) + ".tar.gz"

        with tarfile.open(dlrobot_results_file_name, "w:gz") as tar:
            for f in os.listdir(project_folder):
                tar.add(os.path.join(project_folder, f), arcname=f)

        self.logger.debug(
            "created file {} size={}".format(dlrobot_results_file_name, os.stat(dlrobot_results_file_name).st_size))

        max_send_try_count = 3
        for try_id in range(max_send_try_count):
            conn = None
            try:
                conn = http.client.HTTPConnection(self.args.server_address, timeout=self.args.http_put_timeout)
                with open(dlrobot_results_file_name, "rb") as inp:
                    self.logger.debug("put file {} to {}".format(dlrobot_results_file_name, self.args.server_address))
                    conn.request("PUT", dlrobot_results_file_name, inp.read(), headers=headers)
                    response = conn.getresponse()
                    conn.close()
                    conn = None
                    self.logger.debug("sent dlrobot result file {}, size={}, http_code={}".format(
                        dlrobot_results_file_name,
                        os.stat(dlrobot_results_file_name).st_size,
                        response.status))
                    break
            except Exception as exc:
                self.logger.error('worker got {}'.format(type(exc).__name__))
                self.logger.error('try_id = {} out of {}'.format(try_id, max_send_try_count))
                if conn is not None:
                    conn.close()
                if try_id == max_send_try_count - 1:
                    self.logger.debug("give up, we cannot send the results back, so the results are useless")
                else:
                    sleep_seconds = (try_id + 1) * 180
                    self.logger.debug('sleep for {} seconds'.format(sleep_seconds))
                    time.sleep(sleep_seconds)

        self.logger.debug("delete file {}".format(dlrobot_results_file_name))
        os.unlink(dlrobot_results_file_name)
        shutil.rmtree(project_folder, ignore_errors=True)
        time.sleep(self.args.wait_after_each_doc * len(files))

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
        if self.args.server_address is None:
            self.args.server_address = os.environ['DLROBOT_CENTRAL_SERVER_ADDRESS']
        self.ping_central()

    def dearchive_and_send(self):
        _, ext = os.path.splitext(self.args.archive_path)
        tmp_folder = "tmp"
        unzip = TDearchiver(self.logger, tmp_folder)
        cnt = 0
        files = list()
        for archive_index, filename, normalized_file_name in unzip.dearchive_one_archive(ext, self.args.archive_path, "base"):
            cnt += 1
            files.append(os.path.abspath(normalized_file_name))
            if cnt >= 1000:
                cnt = 0
                self.send_files_to_central(files)
                files = list()
        if len(files) > 0:
            self.send_files_to_central(files)
        shutil.rmtree(tmp_folder, ignore_errors=True)


if __name__ == "__main__":
    unzipper = TUnzipper(TUnzipper.parse_args(sys.argv[1:]))
    unzipper.dearchive_and_send()
