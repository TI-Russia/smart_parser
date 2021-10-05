import re

from common.urllib_parse_pro import strip_scheme_and_query, TUrlUtf8Encode, urlsplit_pro
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
        self.dlrobot_max_time_coeff = 1.0
        self.http_protocol = None
        self.comments = None
        self.redirect_to = None
        self.title = None

    def read_from_json(self, js):
        self.calculated_office_id = js['calc_office_id']
        self.reach_status = js.get('status', TWebSiteReachStatus.normal)
        self.regional_main_pages = js.get('regional')
        self.dlrobot_max_time_coeff = js.get('dlrobot_max_time_coeff', 1.0)
        self.http_protocol = js.get('http_protocol')
        self.comments = js.get('comments')
        self.redirect_to = js.get('redirect_to')
        if self.redirect_to is not None:
            self.ban()
        self.title = js.get('title')
        return self

    def write_to_json(self):
        rec = {
            'calc_office_id': self.calculated_office_id,
        }
        if self.reach_status != TWebSiteReachStatus.normal:
            rec['status'] = self.reach_status
        if self.regional_main_pages is not None:
            rec['regional'] = self.regional_main_pages
        if self.dlrobot_max_time_coeff != 1.0:
            rec['dlrobot_max_time_coeff'] = self.dlrobot_max_time_coeff
        if self.http_protocol is not None:
            rec['http_protocol'] = self.http_protocol
        if self.comments is not None:
            rec['comments'] = self.comments
        if self.redirect_to is not None:
            rec['redirect_to'] = self.redirect_to
        if self.title is not None:
            rec['title'] = self.title
        return rec

    def set_redirect(self, to_url):
        self.redirect_to = to_url
        self.ban()

    def ban(self):
        self.reach_status = TWebSiteReachStatus.abandoned

    def set_protocol(self, protocol):
        self.http_protocol = protocol
        self.reach_status = TWebSiteReachStatus.normal

    def set_title(self, title):
        self.title = title


class TDeclarationWebSiteList:
    disclosures_office_start_id = 20000
    default_input_task_list_path = os.path.join(os.path.dirname(__file__), "data/web_sites.json")

    def __init__(self, logger, file_name=None):
        self.web_sites = dict()
        self.web_domains_redirects = None
        self.web_domain_to_web_site = defaultdict(list)
        self.logger = logger
        if file_name is None:
            self.file_name = TDeclarationWebSiteList.default_input_task_list_path
        else:
            self.file_name = file_name

    def load_from_disk(self):
        with open(self.file_name, "r") as inp:
            for k, v in json.load(inp).items():
                self.web_sites[k] = TDeclarationWebSite().read_from_json(v)
        self.build_web_domains_redirects()
        self.web_domain_to_web_site.clear()
        for k, v in self.web_sites.items():
            self.web_domain_to_web_site[urlsplit_pro(k).hostname].append(k)
        return self

    def build_web_domains_redirects(self):
        self.web_domains_redirects = defaultdict(set)
        for k, v in self.web_sites.items():
            if v.redirect_to is not None:
                d1 = urlsplit_pro(k).hostname
                d2 = urlsplit_pro(v.redirect_to).hostname
                if d1 != d2:
                    self.web_domains_redirects[d1].add(d2)
                    self.web_domains_redirects[d2].add(d1)

    def get_mirrors(self, d: str):
        return self.web_domains_redirects.get(d, set())

    def get_site_by_web_domain(self, web_domain: str) -> TDeclarationWebSite:
        assert '/' not in web_domain
        l = self.web_domain_to_web_site.get(web_domain)
        if l is None:
            return l
        return l[0]

    def get_web_domains(self):
        for k in self.web_domain_to_web_site:
            yield k

    def get_other_sites_regexp_on_the_same_web_domain(self, morda_url):
        web_domain = urlsplit_pro(morda_url).hostname
        other_sites = list()
        for k in self.web_domain_to_web_site.get(web_domain, list()):
            if morda_url.find(k) == -1:
                other_sites.append("({}(/|$))".format(k))
        if len(other_sites) == 0:
            return None
        s = "|".join(other_sites)
        self.logger.debug("use regexp {} to prohibit crawling other projects".format(s))
        return re.compile(s)

    def get_title_by_web_domain(self, web_domain: str) -> str:
        info = self.get_site_by_web_domain(web_domain)
        if info is None or info.title is None:
            return ""
        return info.title

    def add_web_site(self, site_url: str, office_id):
        # russian domain must be in utf8
        assert not TUrlUtf8Encode.is_idna_string(site_url)
        assert not site_url.startswith("http")
        assert site_url not in self.web_sites

        self.logger.debug("add web site {} ".format(site_url))
        s = TDeclarationWebSite()
        s.calculated_office_id = office_id
        self.web_sites[site_url] = s

    def build_office_to_main_website(self, add_http_scheme=True, only_web_domain=False):
        office_to_website = defaultdict(set)
        for site_url, web_site_info in self.web_sites.items():
            if TWebSiteReachStatus.can_communicate(web_site_info.reach_status) and site_url.find('declarator.org') == -1:
                if add_http_scheme:
                    p = web_site_info.http_protocol
                    if p is None:
                        p = "http"
                    url = p + "://" + site_url
                else:
                    url = site_url
                    if only_web_domain:
                        url = urlsplit_pro(site_url).hostname
                office_to_website[web_site_info.calculated_office_id].add(url)
        return office_to_website

    def has_web_site(self, site_url):
        return site_url in self.web_sites

    def get_web_site(self, site_url) -> TDeclarationWebSite:
        return self.web_sites.get(site_url)

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
            web_site = strip_scheme_and_query(o.get('url'))
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
