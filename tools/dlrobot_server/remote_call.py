from common.robot_project import TRobotProject

import os
import time
import json
import sys


class TRemoteDlrobotCall:

    def __init__ (self, worker_ip="", project_file="", exit_code=1, allow_history_formats=False):
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

    def get_total_minutes(self):
        end_time = self.end_time if self.end_time is not None else 0
        return (end_time - self.start_time)  / 69

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

    @staticmethod
    def read_remote_calls_from_file(filename, allow_history_formats=False):
        result = list()
        line_no = 1
        try:
            with open(filename, "r") as inp:
                for line in inp:
                    line = line.strip()
                    remote_call = TRemoteDlrobotCall(allow_history_formats=allow_history_formats)
                    remote_call.read_from_json(line)
                    result.append(remote_call)
                    line_no += 1
        except Exception as exp:
            sys.stderr.write("cannot read file {}, line no {}\n".format(filename, line_no))
            raise
        return result

