from web_site_db.web_sites import TDeclarationWebSiteList
from common.primitives import TUrlUtf8Encode

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
            k = TUrlUtf8Encode.from_idna(k)
        new_web_sites[k] = v
    web_sites.web_sites = new_web_sites
    web_sites.save_to_disk()


