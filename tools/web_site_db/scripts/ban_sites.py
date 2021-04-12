from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.robot_web_site import TWebSiteReachStatus

import argparse
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-list", dest='input_list')
    return parser.parse_args()


if __name__ == '__main__':
    logger = logging.getLogger("ban")
    web_sites = TDeclarationWebSiteList(logger)
    web_sites.load_from_disk()
    args = parse_args()
    with open(args.input_list) as inp:
        for x in inp:
            x = x.strip(" \r\n")
            if web_sites.has_web_site(x):
                web_sites.set_status_to_web_site(x, TWebSiteReachStatus.abandoned)
            else:
                logger.error("skip {}, cannot find this site".format(x))
    web_sites.save_to_disk()


