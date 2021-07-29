from web_site_db.robot_project import TRobotProject
from common.urllib_parse_pro import site_url_to_file_name

import os
import time
import json
import sys
from collections import defaultdict


class TRemoteDlrobotCall:

    def __init__(self, worker_ip="", project_file="", web_site=""):
        self.worker_ip = worker_ip
        self.project_file = project_file
        self.web_site = web_site
        self.exit_code = 1
        self.start_time = int(time.time())
        self.end_time = None
        self.result_files_count = 0
        self.worker_host_name = None
        self.reach_status = None
        self.crawling_timeout = None #not serialized
        self.file_line_index = None

    def task_ended(self):
        return self.end_time is not None

    def task_was_successful(self):
        return self.result_files_count > 0

    def get_website(self):
        return self.web_site

    @staticmethod
    def web_site_to_project_file(s):
        return site_url_to_file_name(s) + ".txt"

    def get_total_minutes(self):
        end_time = self.end_time if self.end_time is not None else 0
        return (end_time - self.start_time) / 60

    def read_from_json(self, str):
        d = json.loads(str)
        self.worker_ip = d['worker_ip']
        self.project_file = d['project_file']
        self.exit_code = d['exit_code']
        self.start_time = d['start_time']
        self.end_time = d['end_time']
        self.result_files_count = d['result_files_count']
        self.worker_host_name = d['worker_host_name']
        self.reach_status = d['reach_status']
        self.web_site = d['web_site']

    def write_to_json(self):
        return {
                'worker_ip': self.worker_ip,
                'project_file': self.project_file,
                'exit_code': self.exit_code,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'result_files_count': self.result_files_count,
                'worker_host_name': self.worker_host_name,
                'reach_status': self.reach_status,
                'web_site': self.web_site
        }

    def calc_project_stats(self, logger, project_folder):
        if not self.task_ended():
            return
        try:
            path = os.path.join(project_folder, self.project_file)
            with TRobotProject(logger, path, [], None, enable_selenium=False,
                               enable_search_engine=False) as project:
                project.read_project(check_step_names=False)
                web_site_snapshot = project.web_site_snapshots[0]
                self.result_files_count = len(web_site_snapshot.export_env.exported_files)
                self.reach_status = web_site_snapshot.reach_status
        except Exception as exp:
            logger.error("Cannot read file {}: exception={}".format(self.project_file, str(exp)))
            pass


class TRemoteDlrobotCallList:
    def __init__(self, logger=None, file_name=None, min_start_time_stamp=None):
        self.remote_calls_by_project_file = defaultdict(list)
        self.last_interaction = defaultdict(int)
        self.logger = logger
        self.min_start_time_stamp = min_start_time_stamp
        if file_name is None:
            self.file_name = os.path.join(os.path.dirname(__file__), "data/dlrobot_remote_calls.dat")
        else:
            self.file_name = file_name
        self.read_remote_calls_from_file()

    def error(self, s):
        if self.logger is not None:
            self.logger.error(s)
        else:
            sys.stderr.write(s + "\n")

    def debug(self, s):
        if self.logger is not None:
            self.logger.debug(s)
        else:
            sys.stderr.write(s + "\n")

    def read_remote_calls_from_file(self):
        self.debug("read {}".format(self.file_name))
        self.remote_calls_by_project_file.clear()
        try:
            with open(self.file_name, "r") as inp:
                line_no = 1
                for line in inp:
                    line = line.strip()
                    remote_call = TRemoteDlrobotCall()
                    remote_call.read_from_json(line)
                    remote_call.file_line_index = line_no
                    self.last_interaction[remote_call.web_site] = max(
                        self.last_interaction[remote_call.web_site],
                        remote_call.start_time
                    )
                    if remote_call.start_time > self.min_start_time_stamp:
                        self.remote_calls_by_project_file[remote_call.project_file].append(remote_call)
                    line_no += 1
        except Exception as exp:
            self.error("cannot read file {}, line no {}\n".format(self.file_name, line_no))
            raise
        return self

    def add_dlrobot_remote_call(self, remote_call: TRemoteDlrobotCall):
        self.remote_calls_by_project_file[remote_call.project_file].append(remote_call)
        with open(self.file_name, "a") as outp:
            outp.write(json.dumps(remote_call.write_to_json(), ensure_ascii=False) + "\n")

    def get_interactions(self, project_file):
        return self.remote_calls_by_project_file.get(project_file, list())

    def has_success(self, project_file):
        for x in self.remote_calls_by_project_file.get(project_file, list()):
            if x.task_was_successful():
                return True
        return False

    def get_all_calls(self):
        for l in self.remote_calls_by_project_file.values():
            for c in l:
                yield c

