from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.web_site_status import TWebSiteReachStatus

import argparse
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    return parser.parse_args()


if __name__ == '__main__':
    logger = logging.getLogger("convert")
    web_sites = TDeclarationWebSiteList(logger)
    web_sites.load_from_disk()
    new_web_sites = dict()
    for k,v in web_sites.web_sites.items():
        if k.startswith("xn--"):
            k = k.encode('latin').decode('idna')
        new_web_sites[k] = v
    web_sites.web_sites = new_web_sites
    web_sites.save_to_disk()


