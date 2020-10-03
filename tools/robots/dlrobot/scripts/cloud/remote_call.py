import os
import time
import json

class TRemoteDlrobotCall:

    def __init__ (self, worker_ip="", project_file="", exit_code=1):
        self.worker_ip = worker_ip
        self.project_file = project_file
        self.exit_code = exit_code
        self.start_time = int(time.time())
        self.end_time = None
        self.result_folder = None
        self.result_files_count = 0
        self.host_name = None

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
        self.result_folder = d['result_folder']
        self.result_files_count = d['result_files_count']
        self.worker_host_name = d['host_name']

    def write_to_json(self):
        return {
                'worker_ip': self.worker_ip,
                'project_file': self.project_file,
                'exit_code': self.exit_code,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'result_folder': self.result_folder,
                'result_files_count': self.result_files_count,
                'host_name': self.worker_host_name
        }

    def calc_project_stats(self):
        if self.result_folder is None:
            return
        summary_file = os.path.join( self.result_folder,  self.project_file + '.result_summary')
        if os.path.exists(summary_file):
            with open(summary_file) as inp:
                self.result_files_count = json.load(inp)['files_count']

    @staticmethod
    def read_remote_calls_from_file(filename):
        result = list()
        with open(filename, "r") as inp:
            for line in inp:
                line = line.strip()
                remote_call = TRemoteDlrobotCall()
                remote_call.read_from_json(line)
                result.append(remote_call)
        return result
