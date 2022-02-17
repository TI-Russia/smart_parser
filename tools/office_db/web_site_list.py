from common.urllib_parse_pro import  urlsplit_pro, get_site_url
from common.web_site_status import TWebSiteReachStatus
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory, TDeclarationWebSite

from collections import defaultdict
import re


class TDeclarationWebSiteList:
    disclosures_office_start_id = 20000

    def __init__(self, logger, offices=None):
        self.web_sites = dict()
        self.web_sites_to_office = dict()
        self.web_domains_redirects = None
        self.web_domain_to_web_site = defaultdict(list)
        self.logger = logger
        if offices is None:
            self.offices = TOfficeTableInMemory()
            self.offices.read_from_local_file()
        else:
            self.offices = offices
        o: TOfficeInMemory
        for o in self.offices.offices.values():
            u:  TDeclarationWebSite
            for u in o.office_web_sites:
                site_url = get_site_url(u.url)
                if site_url in self.web_sites:
                    if site_url in self.web_sites:
                        raise Exception("url {} occurs in office db more than one time".format(site_url))
                self.web_sites[site_url] = u
                self.web_sites_to_office[site_url] = o

        self.build_web_domains_redirects()
        self.web_domain_to_web_site.clear()
        for k, v in self.web_sites.items():
            self.web_domain_to_web_site[TDeclarationWebSiteList.site_url_to_web_domain(k)].append(get_site_url(k))

    @staticmethod
    def site_url_to_web_domain(site_url):
        return urlsplit_pro(site_url).hostname

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

    def get_sites_by_web_domain(self, web_domain: str):
        l = self.web_domain_to_web_site.get(web_domain)
        if l is None:
            if web_domain.startswith('www.'):
                return self.web_domain_to_web_site[web_domain[4:]]
            return list()
        return l

    def get_first_site_by_web_domain(self, web_domain: str) -> TDeclarationWebSite:
        assert '/' not in web_domain
        l = self.get_sites_by_web_domain(web_domain)
        if len(l) == 0:
            return None
        return self.web_sites.get(l[0])

    def get_web_domains(self):
        for k in self.web_domain_to_web_site:
            yield k

    def get_other_sites_regexp_on_the_same_web_domain(self, morda_url):
        web_domain = urlsplit_pro(morda_url).hostname
        other_sites = list()
        for k in self.get_sites_by_web_domain(web_domain):
            if morda_url.find(k) == -1:
                other_sites.append("((www.)?{}(/|$))".format(k))
        if len(other_sites) == 0:
            return None
        s = "|".join(other_sites)
        self.logger.debug("use regexp {} to prohibit crawling other projects".format(s))
        return re.compile(s)

    def get_title_by_web_domain(self, web_domain: str) -> str:
        info = self.get_first_site_by_web_domain(web_domain)
        if info is None or info.title is None:
            return ""
        return info.title

    def has_web_site(self, site_url):
        return site_url in self.web_sites

    def get_web_site(self, site_url) -> TDeclarationWebSite:
        return self.web_sites.get(site_url)

    def get_office(self, site_url) -> TOfficeInMemory:
        return self.web_sites_to_office.get(site_url)

    def check_valid(self, logger, fail_fast=True):
        cnt = 0
        errors = 0
        for site_url, site_info in self.web_sites.items():
            cnt += 1
            if TWebSiteReachStatus.can_communicate(site_info.reach_status):
                if not site_info.url.startswith('http'):
                    errors += 1
                    logger.error("{} has no protocol".format(site_url))
                    if fail_fast:
                        return False
            if site_info.redirect_to is not None:
                if not self.has_web_site(get_site_url(site_info.redirect_to)):
                    errors += 1
                    logger.error("{} has missing redirect {}".format(site_url, site_info.redirect_to))
                    if fail_fast:
                        return False
        self.logger.info("checked {} sites".format(cnt))
        return errors == 0

