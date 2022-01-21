from common.primitives import convert_timeout_to_seconds
from common.download import TDownloadEnv

import json
import os.path
import time


class TRobotConfig:
    # timeouts must have "_timeout" postfix to be updated from program arguments

    def __init__(self, passport_steps=None, max_step_url_count=1000,
                 crawling_timeout=14 * 60 * 60, # 14 hours
                 last_conversion_timeout=30*60,  # 30 minutes
                 export_files_timeout=30*60,
                 selenium_timeout=6,
                 pdf_quota_conversion=20 * 2**20,
                 tar_and_tranfer_timeout=20*60,  # 20 minutes to send data back to central
                 delete_abandoned_folder_timeout= 60 * 60
                 ):
        self.passport_steps = list() if passport_steps is None else passport_steps
        self.max_step_url_count = max_step_url_count
        self.crawling_timeout = crawling_timeout
        self.last_conversion_timeout = last_conversion_timeout
        self.export_files_timeout = export_files_timeout
        self.tar_and_tranfer_timeout = tar_and_tranfer_timeout
        self.delete_abandoned_folder_timeout = delete_abandoned_folder_timeout
        self.selenium_timeout = selenium_timeout
        self.pdf_quota_conversion = pdf_quota_conversion
        self.config_type = None

    @staticmethod
    def read_from_file(file_path):
        with open(file_path) as inp:
            return TRobotConfig.read_from_json(json.load(inp))

    @staticmethod
    def read_by_config_type(config_type):
        file_path = os.path.join(os.path.dirname(__file__), "..", "robot", "configs", config_type + ".json")
        assert os.path.exists(file_path)
        c = TRobotConfig.read_from_file(file_path)
        c.config_type = config_type
        return c

    def read_timeout(self, d, key):
        if key in d:
            a  = d[key]
            if isinstance(a, str):
                a = convert_timeout_to_seconds(a)
            assert isinstance(a, int)
            assert hasattr(self, key)
            setattr(self, key, a)

    @staticmethod
    def read_from_json(d):
        c = TRobotConfig()
        c.passport_steps = d.get('robot_steps', c.passport_steps)
        c.max_step_url_count = d.get('max_step_url_count', c.max_step_url_count)
        c.read_timeout(d, 'crawling_timeout')
        c.read_timeout(d, 'last_conversion_timeout')
        c.read_timeout(d, 'selenium_timeout')
        c.read_timeout(d, 'export_files_timeout')
        c.set_pdf_quota_conversion(d.get('pdf_quota_conversion', c.pdf_quota_conversion))
        return c

    def set_pdf_quota_conversion(self, v):
        self.pdf_quota_conversion = v
        TDownloadEnv.PDF_QUOTA_CONVERSION = v

    def get_step_passports(self):
        return self.passport_steps

    def get_step_index_by_name(self, name):
        if name is None:
            return -1
        for i, r in enumerate(self.get_step_passports()):
            if name == r['step_name']:
                return i
        raise Exception("cannot find step {}".format(name))

    def get_dlrobot_total_timeout(self):
        return self.crawling_timeout + self.last_conversion_timeout + self.export_files_timeout

    def get_kill_timeout_in_central(self):
        return self.get_dlrobot_total_timeout() + self.tar_and_tranfer_timeout

    def get_timeout_to_delete_files_in_worker(self):
        return self.get_kill_timeout_in_central() + self.delete_abandoned_folder_timeout

    def update_from_program_args(self, args):
        if args.max_step_url_count is not None:
            self.max_step_url_count = args.max_step_url_count
        if args.pdf_quota_conversion is not None:
            self.set_pdf_quota_conversion(args.pdf_quota_conversion)

        for timeout_name in dir(args):
            if timeout_name.endswith("_timeout"):
                v = getattr(args, timeout_name)
                if v is not None:
                    setattr(self, timeout_name, convert_timeout_to_seconds(v))

    def have_time_for_last_dl_recognizer(self, start_time):
        total_timeout = self.get_dlrobot_total_timeout()
        if total_timeout == 0:
            return True
        future_kill_time = start_time + total_timeout
        if time.time() + 20*60 > future_kill_time:
            #we need at least 20 minutes to export files
            return False
        return True
