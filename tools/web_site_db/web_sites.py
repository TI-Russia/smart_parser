from common.primitives import get_site_domain_wo_www, TUrlUtf8Encode
from web_site_db.web_site_status import TWebSiteReachStatus

import json
import os
from collections import defaultdict
import datetime


class TDeclarationWebSite:
    def __init__(self):
        self.calculated_office_id = None
        self.reach_status = TWebSiteReachStatus.normal
        self.regional_main_pages = None
        self.disable_selenium = None
        self.dlrobot_max_time_coeff = 1.0
        self.http_protocol = None
        self.comments = None
        self.redirect_to = None
        self.start_sub_page = None

    def read_from_json(self, js):
        self.calculated_office_id = js['calc_office_id']
        self.reach_status = js.get('status', TWebSiteReachStatus.normal)
        self.regional_main_pages = js.get('regional')
        self.disable_selenium = js.get('disable_selenium')
        self.dlrobot_max_time_coeff = js.get('dlrobot_max_time_coeff', 1.0)
        self.http_protocol = js.get('http_protocol')
        self.comments = js.get('comments')
        self.redirect_to = js.get('redirect_to')
        if self.redirect_to is not None:
            self.ban()
        self.start_sub_page = js.get('start_sub_page')
        return self

    def write_to_json(self):
        rec = {
            'calc_office_id': self.calculated_office_id,
        }
        if self.reach_status != TWebSiteReachStatus.normal:
            rec['status'] = self.reach_status
        if self.regional_main_pages is not None:
            rec['regional'] = self.regional_main_pages
        if self.disable_selenium is not None:
            rec['disable_selenium'] = self.disable_selenium
        if self.dlrobot_max_time_coeff != 1.0:
            rec['dlrobot_max_time_coeff'] = self.dlrobot_max_time_coeff
        if self.http_protocol is not None:
            rec['http_protocol'] = self.http_protocol
        if self.comments is not None:
            rec['comments'] = self.comments
        if self.redirect_to is not None:
            rec['redirect_to'] = self.redirect_to
        if self.start_sub_page is not None:
            rec['start_sub_page'] = self.start_sub_page
        return rec

    def set_redirect(self, to_url):
        self.redirect_to = to_url
        self.ban()

    def ban(self):
        self.reach_status = TWebSiteReachStatus.abandoned

    def set_protocol(self, protocol):
        self.http_protocol = protocol
        self.reach_status = TWebSiteReachStatus.normal


class TDeclarationWebSiteList:
    disclosures_office_start_id = 20000
    default_input_task_list_path = os.path.join(os.path.dirname(__file__), "data/web_sites.json")

    def __init__(self, logger, file_name=None):
        self.web_sites = dict()
        self.logger = logger
        if file_name is None:
            self.file_name = TDeclarationWebSiteList.default_input_task_list_path
        else:
            self.file_name = file_name

    def load_from_disk(self):
        with open(self.file_name, "r") as inp:
            for k, v in json.load(inp).items():
                self.web_sites[k] = TDeclarationWebSite().read_from_json(v)
        return self

    def add_web_site(self, web_site, office_id):
        # russian domain must be in utf8
        assert not TUrlUtf8Encode.is_idna_string(web_site)

        self.logger.debug("add web site {} ".format(web_site))
        assert web_site not in self.web_sites
        s = TDeclarationWebSite()
        s.calculated_office_id = office_id
        self.web_sites[web_site] = s

    def build_office_to_main_website(self):
        office_to_website = defaultdict(set)
        for web_domain, web_site in self.web_sites.items():
            if TWebSiteReachStatus.can_communicate(web_site.reach_status) and web_domain != 'declarator.org':
                p = web_site.http_protocol
                if p is None:
                    p = "http"
                url = p + "://" + web_domain
                office_to_website[web_site.calculated_office_id].add(url)
        return office_to_website

    def has_web_site(self, web_site):
        return web_site in self.web_sites

    def get_web_site(self, web_site) -> TDeclarationWebSite:
        return self.web_sites.get(web_site)

    def save_to_disk(self):
        with open(self.file_name, "w") as outp:
            js = dict( (k, v.write_to_json()) for (k, v) in self.web_sites.items())
            json.dump(js, outp, indent=4, ensure_ascii=False)

    def add_new_websites_from_declarator(self, website_to_most_freq_office):
        errors = list()
        for web_site, calculated_office_id in website_to_most_freq_office.items():
            if web_site not in self.web_sites:
                self.add_web_site(web_site, calculated_office_id)
            elif self.web_sites[web_site].calculated_office_id >= self.disclosures_office_start_id:
                errors.append("web site: {}, declarator office id: {}, disclosures office id: {}".format(
                    web_site, calculated_office_id, self.web_sites[web_site].calculated_office_id))
        if len(errors) > 0:
            file_name = "conflict_offices.txt"
            with open(file_name, "w") as outp:
                for x in errors:
                    outp.write(x + "\n")
            raise Exception ("there are web sites that are referenced in disclosures web_site_snapshots and declarator web_site_snapshots" +
                              "we have to office ambiguity. These web sites are written to {}".format(file_name))

    def update_from_office_urls(self, offices, logger):
        for o in offices:
            web_site = get_site_domain_wo_www(o.get('url'))
            if web_site not in self.web_sites:
                self.add_web_site(web_site, o['id'])
                logger.info ('add a website {} from office.url'.format(web_site))


class BadFormat(Exception):

    def __init__(self, message="bad format"):
        """Initializer."""
        self.message = message
    def __str__(self):
        return self.message


class TDeclarationRounds:
    default_dlrobot_round_path = os.path.join(os.path.dirname(__file__), "data/dlrobot_rounds.json")

    def __init__(self, file_name=None):
        self.rounds = list()
        self.start_time_stamp = None
        if file_name is None:
            self.file_name = TDeclarationRounds.default_dlrobot_round_path
        else:
            self.file_name = file_name
        if not os.path.exists(self.file_name):
            raise BadFormat("File {} does not exist".format(self.file_name))
        with open(self.file_name, "r") as inp:
            self.rounds = json.load(inp)
        for r in self.rounds:
            t = datetime.datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M')
            self.start_time_stamp = t.timestamp()
        if len(self.rounds) == 0:
            raise BadFormat("no dlrobot information in {}".format(self.file_name))
        if self.rounds[-1].get('finished', False):
            raise BadFormat("no current round found, please add a new record to {} in order to create to a new round".format(self.file_name))

    @staticmethod
    def build_an_example(date):
        return [
              {"start_time": date.strftime('%Y-%m-%d %H:%M'), "finished": False}
        ]
