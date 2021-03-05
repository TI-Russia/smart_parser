from dlrobot_server.common_server_worker import DLROBOT_HEADER_KEYS
from common.archives import TDearchiver
from common.robot_project import TRobotProject
from common.robot_web_site import TWebSiteReachStatus
from common.export_files import TExportFile

import argparse
import logging
import os
import sys
import time
import http.server
import shutil
import tarfile
import platform



def setup_logging(logfilename):
    logger = logging.getLogger("archiver")
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

def include_fns_json_to_html(json_path, html_path):
    assert json_path.endswith('json')
    assert html_path.endswith('html')
    with open(json_path) as inp:
        filters = json.load(inp)['filters']

    if 'insp_name' in filters:
        department = filters['insp_name']
    else:
        department = filters.get('upr_name', '')

    if filters.get('otdel_name') is not None:
        if len(department) > 0:
            department += '; '
        department += filters.get('otdel_name')

    with open(html_path, "rb") as inp:
        file_data = inp.read().strip()
        if file_data.endswith(b'<html>'):
            file_data = file_data[:-len('<html>')] + b'</html>'
        soup = BeautifulSoup(file_data, "html.parser")
    metatag = soup.new_tag('meta')
    metatag.attrs['name'] = 'smartparser_department'
    metatag.attrs['content'] = department
    soup.html.insert(2, metatag)

    with open(html_path, "w") as outp:
        outp.write(str(soup))


class TUnzipper:
    def __init__(self, args):
        self.args = args
        self.working = True
        self.logger = setup_logging(self.args.log_file_name)
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
        parser.add_argument("--fns-prepare", dest='fns_prepare', required=False, action="store_true")
        args = parser.parse_args(arg_list)
        return args

    def send_files_to_central(self, files):
        project_folder = self.args.web_domain
        shutil.rmtree(project_folder, ignore_errors=True)
        os.mkdir(project_folder)
        os.chdir(project_folder)

        robot_project_path = os.path.join(self.args.web_domain + ".txt")
        TRobotProject.create_project(self.args.web_domain, robot_project_path)
        os.makedirs(os.path.join("result", self.args.web_domain), exist_ok=True)
        with TRobotProject(self.logger, robot_project_path, [], None, enable_selenium=False,
                           enable_search_engine=False) as project:
            project.add_office(self.args.web_domain)
            project.offices[0].reach_status = TWebSiteReachStatus.normal
            export_env = project.offices[0].export_env
            for file_name in files:
                export_path = os.path.join("result", self.args.web_domain, os.path.basename(file_name))
                shutil.move(file_name, export_path)
                export_file = TExportFile(url=self.args.web_domain, export_path=export_path)
                export_env.exported_files.append(export_file)
            project.write_project()
        os.chdir("..")

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
            if self.args.fns_prepare:
                json_path = os.path.splitext(normalized_file_name)[0] + ".json"
                if os.path.exists(json_path):
                    include_fns_json_to_html(json_path, normalized_file_name)
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
