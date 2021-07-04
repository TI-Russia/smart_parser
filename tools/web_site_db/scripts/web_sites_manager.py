from web_site_db.web_sites import TDeclarationWebSiteList
from web_site_db.web_site_status import TWebSiteReachStatus
from common.primitives import  TUrlUtf8Encode
from common.logging_wrapper import setup_logging
from copy import  deepcopy
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be ban, to_utf8, mvd")
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--ban-list", dest='ban_list', required=False)
    return parser.parse_args()


class TWebSitesManager:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("web_sites")
        self.in_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.input_file)
        self.in_web_sites.load_from_disk()
        self.out_web_sites = TDeclarationWebSiteList(self.logger, file_name=self.args.output_file)

    def ban_sites(self):
        with open(self.args.ban_list) as inp:
            self.out_web_sites.web_sites = self.in_web_sites.web_sites
            for x in inp:
                x = x.strip(" \r\n")
                if self.out_web_sites.has_web_site(x):
                    self.out_web_sites.set_status_to_web_site(x, TWebSiteReachStatus.abandoned)
                else:
                    self.out_web_sites.logger.error("skip {}, cannot find this site".format(x))

    def to_utf8(self):
        for k,v in self.in_web_sites.web_sites.items():
            if TUrlUtf8Encode.is_idna_string(k):
                k = TUrlUtf8Encode.from_idna(k)
            self.out_web_sites.web_sites[k] = v

    def convert_mvd(self):
        new_web_sites = dict()
        for k, v in self.in_web_sites.web_sites.items():
            self.out_web_sites.web_sites[k] = v
            if k.endswith('.mvd.ru'):
                key = k[:-len('.mvd.ru')] + '.мвд.рф'
                if key not in self.in_web_sites.web_sites:
                    self.out_web_sites.web_sites[key] = deepcopy(v)
                v.reach_status = TWebSiteReachStatus.abandoned
            self.out_web_sites.web_sites[k] = v

    def main(self):
        if self.args.action == "ban":
            self.ban_sites()
        elif self.args.action == "to_utf":
            self.to_utf8()
        elif self.args.action == "mvd":
            self.convert_mvd()
        else:
            raise Exception("unknown action")
        self.out_web_sites.save_to_disk()


if __name__ == '__main__':
    m = TWebSitesManager()
    m.main()


