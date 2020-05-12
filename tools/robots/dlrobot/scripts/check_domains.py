import argparse
import sys
import re
import json
from robots.common.http_request import make_http_request_urllib, RobotHttpException, make_http_request_curl, TRequestPolicy
from multiprocessing.dummy import Pool as ThreadPool
import random
from functools import partial
import logging
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-files", help='a file from ../../disclosures/scripts/create_json_by_human_files.py',
                        dest='human_files', required=False)
    parser.add_argument("--domains-list", dest='input_domains', required=False)
    parser.add_argument("--reached-domains", dest='output_domains', required=True, default="domains.txt")
    parser.add_argument("--process-count", dest='process_count', type=int, default=30)
    parser.add_argument("--timeouted-domains", dest='bad_domains', required=False, default="timeouted-domains.txt")
    args = parser.parse_args()
    return args


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

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    return logger


def check_alive(logger, url):
    try:
        make_http_request_urllib(logger, url, 'HEAD')
        logger.debug('urllib {} -> success\n'.format(url))
        return url
    except RobotHttpException as exp:
        logger.debug('urllib failed for {}\n'.format(url))
        pass

    try:
        make_http_request_curl(logger, url, 'HEAD')
        logger.debug('try with curl {} -> success\n'.format(url))
        return url
    except RobotHttpException as exp:
        logger.debug('curl failed for {}\n'.format(url))
        return None


def read_input(args):
    if args.human_files is not None:
        with open(args.human_files, "r", encoding="utf8") as inpf:
            human_files = json.load(inpf)
        urls = list(set(x['domain'] for x in human_files.values() if len(x['domain']) > 0))
    else:
        assert args.input_domains is not None
        urls = list()
        with open(args.input_domains, "r", encoding="utf8") as inpf:
            for x in inpf:
                x = x.strip(" \r\n")
                if len(x) > 0:
                    urls.append(x)

    urls = list(d for d in urls if re.match('^to[0-9][0-9].rosreestr.ru', d) is None)  #deleted and very heavy
    random.shuffle(urls)
    #urls = list(urls)[0:300]
    sys.stderr.write("we are going to process {} urls in {} processes\n".format(len(urls), args.process_count))
    return urls


def write_output(args, urls, results):
    good_domains = set(x for x in results if x is not None)
    sys.stderr.write("\ncan reach {} domains out of {}\n".format(len(good_domains), len(urls)))
    sys.stderr.write("write to  {}\n".format(args.output_domains))
    with open(args.output_domains, "w", encoding="utf8") as outf:
        for d in good_domains:
            outf.write('{}\n'.format(d))
    sys.stderr.write("write to  {}\n".format(args.bad_domains))
    with open(args.bad_domains, "w", encoding="utf8") as outf:
        for d in urls:
            if d not in good_domains:
                outf.write('{}\n'.format(d))


if __name__ == "__main__":
    TRequestPolicy.ENABLE = False
    logger = setup_logging('check_domains.log')
    args = parse_args()
    urls = read_input(args)
    pool = ThreadPool(args.process_count)
    results = pool.map(partial(check_alive, logger), urls)
    pool.close()
    pool.join()
    write_output(args, urls, results)

