import os
import shutil
import json


class DLROBOT_HTTP_CODE:
    NO_MORE_JOBS = 530
    TOO_BUSY = 531


class DLROBOT_HEADER_KEYS:
    WORKER_HOST_NAME = "worker_host_name"
    EXIT_CODE= "exitcode"
    PROJECT_FILE = "dlrobot_project_file_name"
    CRAWLING_TIMEOUT = "dlrobot_project_crawling_timeout"


class TTimeouts:
    # must have "_TIMEOUT" postfix for testing purposes
    MAIN_CRAWLING_TIMEOUT = 3 * 60 * 60  # 3h
    WAIT_CONVERSION_TIMEOUT = 30 * 60  # 30m
    EXPORT_FILES_TIMEOUT = 30 * 60  # 30m to export files
    TAR_AND_TRANSFER_TIMEOUT = 20 * 60  # 20 minutes to send data back to central
    DELETE_ABANDONED_FOLDER_TIMEOUT = 60 * 60

    @staticmethod
    def save_timeouts():
        return dict((x, TTimeouts.__dict__[x]) for x in dir(TTimeouts) if x.endswith("TIMEOUT"))

    @staticmethod
    def set_timeouts(timeout):
        for x in dir(TTimeouts):
            if x.endswith("TIMEOUT"):
                setattr(TTimeouts, x, timeout)

    @staticmethod
    def restore_timeouts(timeouts):
        for k,v in timeouts.items():
            setattr(TTimeouts, k, v)

    @staticmethod
    def get_kill_timeout_in_worker(crawling_timeout):
        return crawling_timeout + TTimeouts.WAIT_CONVERSION_TIMEOUT + TTimeouts.EXPORT_FILES_TIMEOUT

    @staticmethod
    def get_kill_timeout_in_central(crawling_timeout):
        return TTimeouts.get_kill_timeout_in_worker(crawling_timeout) + \
               TTimeouts.TAR_AND_TRANSFER_TIMEOUT

    @staticmethod
    def get_timeout_to_delete_files_in_worker(crawling_timeout):
        return TTimeouts.get_kill_timeout_in_central(crawling_timeout) + TTimeouts.DELETE_ABANDONED_FOLDER_TIMEOUT

PITSTOP_FILE = ".dlrobot_pit_stop"


def find_yandex_console_utility():
    yandex_cloud_console = shutil.which('yc')
    if yandex_cloud_console is None:
        yandex_cloud_console = os.path.expanduser('~/yandex-cloud/bin/yc')
        if not os.path.exists(yandex_cloud_console):
            raise FileNotFoundError(
                "install yandex cloud console ( https://cloud.yandex.ru/docs/cli/operations/install-cli )")
    return yandex_cloud_console


class TYandexCloud:
    yandex_cloud_console = None

    @staticmethod
    def get_yc():
        if TYandexCloud.yandex_cloud_console is None:
            TYandexCloud.yandex_cloud_console = find_yandex_console_utility()
        return TYandexCloud.yandex_cloud_console

    @staticmethod
    def start_yandex_cloud_worker(id):
        cmd = "{} compute instance start {}".format(TYandexCloud.get_yc(), id)
        os.system(cmd)

    @staticmethod
    def list_instances():
        cmd = "{} compute instance list --format json >yc.json".format(TYandexCloud.get_yc())
        os.system(cmd)
        with open("yc.json", "r") as inp:
            yc_json = json.load(inp)
        os.unlink("yc.json")
        return yc_json

    @staticmethod
    def get_worker_ip(one_record):
        return one_record['network_interfaces'][0]['primary_v4_address']['one_to_one_nat']['address']


