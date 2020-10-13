import os
from robots.common.download import TDownloadEnv, TDownloadedFile
from robots.common.http_request import TRequestPolicy
import logging
import argparse


def setup_logging(logfilename):
    logger = logging.getLogger("dlrobot_logger")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", dest='url', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    logger = setup_logging("dlrobot.log")
    args = parse_args()
    TDownloadEnv.clear_cache_folder()
    TRequestPolicy.ENABLE = False

    #see https://stackoverflow.com/questions/38015537/python-requests-exceptions-sslerror-dh-key-too-small
    #for http://primorie.fas.gov.ru
    file = TDownloadedFile(args.url)
    assert file is not None
