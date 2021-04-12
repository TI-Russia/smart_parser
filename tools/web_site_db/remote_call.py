import re

from web_site_db.robot_project import TRobotProject
from web_site_db.robot_web_site import TWebSiteReachStatus
import os
import time
import json
import sys
from collections import defaultdict


class TRemoteDlrobotCall:

    def __init__(self, worker_ip="", project_file="", exit_code=1, allow_history_formats=False):
        self.worker_ip = worker_ip
        self.project_file = project_file
        self.exit_code = exit_code
        self.start_time = int(time.time())
        self.end_time = None
        self.project_folder = None
        self.result_files_count = 0
        self.worker_host_name = None
        self.reach_status = None
        self.allow_history_formats = allow_history_formats

    def get_website(self):
        website = self.project_file
        if website.endswith(".txt"):
            website = website[:-len(".txt")]
        return website

    @staticmethod
    def project_file_to_web_site(s):
        s = s.replace('_port_delim_', ':')
        assert s.endswith('.txt')
        return s[:-4]

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
        self.project_folder = d['result_folder']
        self.result_files_count = d['result_files_count']
        self.worker_host_name = d['worker_host_name']
        if not self.allow_history_formats:
            self.reach_status = d['reach_status']
        else:
            self.reach_status = d.get('reach_status')

    def write_to_json(self):
        return {
                'worker_ip': self.worker_ip,
                'project_file': self.project_file,
                'exit_code': self.exit_code,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'result_folder': self.project_folder,
                'result_files_count': self.result_files_count,
                'worker_host_name': self.worker_host_name,
                'reach_status': self.reach_status
        }

    def calc_project_stats(self, logger):
        if self.project_folder is None:
            return
        try:
            path = os.path.join(self.project_folder, self.project_file)
            with TRobotProject(logger, path, [], None, enable_selenium=False,
                               enable_search_engine=False) as project:
                project.read_project(check_step_names=False)
                office_info = project.offices[0]
                self.result_files_count = len(office_info.export_env.exported_files)
                self.reach_status = office_info.reach_status
        except Exception as exp:
            pass


class TRemoteDlrobotCallList:
    def __init__(self, logger=None, file_name=None, allow_history_formats=False):
        self.remote_calls_by_project_file = defaultdict(list)
        self.logger = logger
        self.allow_history_formats = allow_history_formats
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
        line_no = 1

        try:
            with open(self.file_name, "r") as inp:
                for line in inp:
                    line = line.strip()
                    remote_call = TRemoteDlrobotCall(allow_history_formats=self.allow_history_formats)
                    remote_call.read_from_json(line)
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

