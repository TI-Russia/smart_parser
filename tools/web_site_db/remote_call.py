import re

from web_site_db.robot_project import TRobotProject
from web_site_db.web_site_status import TWebSiteReachStatus
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

    def get_website(self):
        return self.web_site

    @staticmethod
    def web_site_to_project_file(s):
        s = re.sub('(:)(?=[0-9])', '_port_delim_', s)
        return s + ".txt"

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
    def __init__(self, logger=None, file_name=None):
        self.remote_calls_by_project_file = defaultdict(list)
        self.logger = logger
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
                    self.remote_calls_by_project_file[remote_call.project_file].append(remote_call)
                    line_no += 1
        except Exception as exp:
            self.error("cannot read file {}, line no {}\n".format(self.file_name, line_no))
            raise
        return self

    def add_dlrobot_remote_call(self, remote_call: TRemoteDlrobotCall):
        self.remote_calls_by_project_file[remote_call.project_file].append(remote_call)
        with open(self.file_name, "a") as outp:
            outp.write(json.dumps(remote_call.write_to_json()) + "\n")

    def get_interactions_count(self, project_file):
        return len(self.remote_calls_by_project_file[project_file])

    def get_min_interactions_count(self):
        if len(self.remote_calls_by_project_file) == 0:
            return 0
        else:
            return min(len(x) for x in self.remote_calls_by_project_file.values())

    def get_last_failures_count(self, project_file):
        l = list(self.remote_calls_by_project_file[project_file])
        l.sort(key=lambda x: -x.start_time)
        failures_cnt = 0
        for i in l:
            if TWebSiteReachStatus.can_communicate(i.reach_status):
                break
            failures_cnt += 1
        return failures_cnt

    def get_all_calls(self):
        for l in self.remote_calls_by_project_file.values():
            for c in l:
                yield c

