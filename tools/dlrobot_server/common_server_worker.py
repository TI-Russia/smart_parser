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


class  TTimeouts:
    MAIN_CRAWLING_TIMEOUT = 3*60*60  # 3h
    WAIT_CONVERSION_TIMEOUT = 30*60  # 30m

    # 30m # may be additional 30 min to export files, it makes 4h
    MAX_EXPORT_ESTIMATION_TIME = 30 * 60

    # after this timeout(4h) dlrobot.py must be stopped and the results are not considered
    OVERALL_HARD_TIMEOUT_IN_WORKER =  MAIN_CRAWLING_TIMEOUT + WAIT_CONVERSION_TIMEOUT + MAX_EXPORT_ESTIMATION_TIME

    #add 20 minutes to send data back to central
    OVERALL_HARD_TIMEOUT_IN_CENTRAL = OVERALL_HARD_TIMEOUT_IN_WORKER + 20*60

    TIMEOUT_IN_WORKER_CLEAN_JUNK = OVERALL_HARD_TIMEOUT_IN_WORKER + 60 * 60 # 5 hours


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


