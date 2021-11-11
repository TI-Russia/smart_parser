import json
import os
import shutil
import sys


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
        try:
            return one_record['network_interfaces'][0]['primary_v4_address']['one_to_one_nat']['address']
        except KeyError as exp:
            sys.stderr.write("cannot process {}, Exception={}".format(one_record, exp))
            raise


def find_yandex_console_utility():
    yandex_cloud_console = shutil.which('yc')
    if yandex_cloud_console is None:
        yandex_cloud_console = os.path.expanduser('~/yandex-cloud/bin/yc')
        if not os.path.exists(yandex_cloud_console):
            raise FileNotFoundError(
                "install yandex cloud console ( https://cloud.yandex.ru/docs/cli/operations/install-cli )")
    return yandex_cloud_console