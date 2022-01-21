from common.logging_wrapper import setup_logging

import argparse
import webdav.client as wc
import os
from pathlib import Path
import json
import time
import datetime


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action",  dest="action", help="can be upload, download, info, mkdir, publish, delete, sync")

    parser.add_argument("--connect-info",  dest="connect_info", default=os.path.join(Path.home(), ".webdav"))
    parser.add_argument('--local-path', dest="local_path")
    parser.add_argument('--cloud-path', dest="cloud_path")
    parser.add_argument('--verbose', dest="verbose", action="store_true", default=False)
    parser.add_argument('--exclude-dirs', dest="exclude_dirs")
    parser.add_argument('--report-output-file', dest="report_output_file")
    parser.add_argument('--wait', dest="wait", action="store_true", default=False)
    args = parser.parse_args()
    return args


class TYandexDiskClient:
    lock_file = '/tmp/yandex-disk.lockfile'

    def __init__(self, logger, connect_file_path, verbose):
        self.logger = logger
        self.verbose = verbose
        self.client = self.connect(connect_file_path)

    def connect(self, connect_file_path):
        with open(connect_file_path, "r")  as inp:
            options = json.load(inp)
        if self.verbose:
            options['verbose'] = True
        return wc.Client(options)

    def info(self, cloud_path):
        return self.client.info(cloud_path)

    def mkdir(self, cloud_path):
        return self.client.mkdir(cloud_path)

    def upload(self, local_path, cloud_path):
        def print_progress(download_total, downloaded, upload_total, uploaded):
            print("{}/{}".format(uploaded, upload_total))
        x = self.client.upload(cloud_path, local_path, print_progress if self.verbose else None)

    def download(self, local_path, cloud_path):
        def print_progress(download_total, downloaded, upload_total, uploaded):
            print("{}/{}".format(downloaded, download_total))
        return self.client.download(cloud_path, local_path, print_progress if self.verbose else None)

    def publish(self, cloud_path):
        return self.client.publish(cloud_path)

    def publish_special(self, cloud_path, report_output_file):
        url = self.client.publish(cloud_path)
        file_size = int(self.client.info(cloud_path)['size'])
        date = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
        with open(report_output_file, "w") as outp:
            outp.write("Полный sql-дамп (mysql 8.0 и выше): <a href=\"{}\">скачать c Яндекс-диска</a> (date={}, size={})".format(
                url, date, file_size))

    def delete(self, cloud_path):
        return self.client.clean(cloud_path)

    def is_locked(self):
        return os.path.exists(self.lock_file)

    def log_and_system(self, cmd):
        self.logger.info(cmd)
        exitcode = os.system(cmd)
        if exitcode != 0:
            raise Exception("Error, {} returned {}".format(cmd, exitcode))

    def create_lock_file(self):
        with open(self.lock_file, "w") as outp:
            pass

    def delete_lock_file(self):
        os.unlink(self.lock_file)

    def sync(self, exclude_dirs, wait):
        if self.is_locked():
            if not wait:
                self.logger.info("could not start the second instance of yandex-disk")
                return
            else:
                start_time = time.time()
                while self.is_locked():
                    self.logger.debug("wait 1m")
                    time.sleep(60)
                    if time.time() - start_time > 60 * 60 * 3:
                        self.logger.info("could wait more than 3 hours")
                        return
        cmd = "yandex-disk sync"
        if exclude_dirs is not None:
            cmd += " --exclude-dirs={}".format(exclude_dirs)
        try:
            self.create_lock_file()
            self.log_and_system(cmd)
        finally:
            self.delete_lock_file()


def main():
    args = parse_args()
    logger = setup_logging("yandex-disk")
    client = TYandexDiskClient(logger, args.connect_info, args.verbose)
    if args.action == "info":
        print(client.info(args.cloud_path))
    elif args.action == "mkdir":
        client.mkdir(args.cloud_path)
    elif args.action == "upload":
        client.upload(args.local_path, args.cloud_path)
    elif args.action == "download":
        client.upload(args.local_path, args.cloud_path)
    elif args.action == "publish":
        print(client.publish(args.cloud_path))
    elif args.action == "publish_special":
        print(client.publish_special(args.cloud_path, args.report_output_file))
    elif args.action == "delete":
        print(client.delete(args.cloud_path))
    elif args.action == "sync":
        client.sync(args.exclude_dirs, args.wait)
    logger.debug("all done")


if __name__ == "__main__":
    main()


