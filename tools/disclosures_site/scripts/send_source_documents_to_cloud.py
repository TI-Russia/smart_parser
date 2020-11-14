import shutil
import os
import argparse
import logging
import psutil


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
    return parser.parse_args()


def create_tar_file(logger, args):
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
    return tar_file


def check_yandex_disk_is_running():
    for proc in psutil.process_iter():
        cmdline = " ".join(proc.cmdline())
        if proc.pid != os.getpid():
            if 'yandex-disk' in cmdline:
                return True
    return False


def main(args):
    logger = setup_logging("backuper.log")
    assert check_yandex_disk_is_running()

    tar_file = create_tar_file(logger, args)

    logger.info("move {} to {}".format(tar_file, args.output_cloud_folder))
    shutil.move(tar_file, args.output_cloud_folder)

    logger.info("all done")


if __name__ == '__main__':
    args = parse_args()
    main(args)
