from declarations.input_json import TSourceDocument, TDlrobotHumanFile, TWebReference, TIntersectionStatus
import shutil
import os
import re
import argparse
import hashlib
import logging
from collections import defaultdict
from robots.common.robot_project import TRobotProject
import yadisk

def setup_logging(logfilename):
    logger = logging.getLogger("backuper")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ctime", dest='max_ctime', required=True, type=int, help="max ctime of an input folder")
    parser.add_argument("--input-dlrobot-folder", dest='input_dlrobot_folder', required=True)
    parser.add_argument("--output-cloud-folder", dest='output_cloud_folder', required=True)
    parser.add_argument("--yandex-disk-token-file", dest='yandex_disk_token_file',
                        required=False, default=os.path.expanduser("~/.yandex_token"))
    return parser.parse_args()


def main(args):
    logger = setup_logging("backuper.log")

    with open (args.yandex_disk_token_file) as inp:
        yandex_disk = yadisk.YaDisk(token=inp.read().strip())
        assert yandex_disk.check_token()
        logger.info("check {} exists in the cloud".format(args.output_cloud_folder))
        assert yandex_disk.exists(args.output_cloud_folder)

    tmp_folder = "dlrobot.{}".format(args.max_ctime)
    os.mkdir(tmp_folder)
    with os.scandir(args.input_dlrobot_folder) as it:
        for entry in it:
            if entry.is_dir() and entry.stat().st_ctime < args.max_ctime:
                logger.info("move {} {}".format(entry.name, tmp_folder))
                shutil.move(os.path.join(args.input_dlrobot_folder, entry.name), tmp_folder)
    tar_file = "dlrobot.{}.tar.gz".format(args.max_ctime)

    cmd = "tar cfz {} {}".format(tar_file, tmp_folder)
    logger.info(cmd)
    os.system(cmd)

    logger.info("remove {}".format(tmp_folder))
    shutil.rmtree(tmp_folder, ignore_errors=True)

    logger.info("upload  {} to {}".format(tar_file, args.output_cloud_folder))
    yandex_disk.upload(tar_file, os.path.join(args.output_cloud_folder, tar_file))


if __name__ == '__main__':
    args = parse_args()
    main(args)
