from common.primitives import get_site_domain_wo_www
from web_site_db.web_site_status import TWebSiteReachStatus

import json
import os
from collections import defaultdict


class TDeclarationWebSite:
    def __init__(self):
        self.calculated_office_id = None
        self.reach_status = TWebSiteReachStatus.normal
        self.regional_main_pages = None
        self.disable_selenium = None

    def read_from_json(self, js):
        self.calculated_office_id = js['calc_office_id']
        self.reach_status = js.get('status', TWebSiteReachStatus.normal)
        self.regional_main_pages = js.get('regional')
        self.disable_selenium = js.get('disable_selenium')
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
        return rec


class TDeclarationWebSiteList:
    disclosures_office_start_id = 20000
    default_input_task_list_path = os.path.join(os.path.dirname(__file__), "data/web_sites.json")

    def __init__(self, logger, file_name=None):
        self.web_sites = dict()
        self.logger = logger
        if file_name is None:
            self.file_name = os.path.join(os.path.dirname(__file__), "data/web_sites.json")
        else:
            self.file_name = file_name

    def load_from_disk(self):
        with open(self.file_name, "r") as inp:
            for k, v in json.load(inp).items():
                self.web_sites[k] = TDeclarationWebSite().read_from_json(v)
        return self

    def add_web_site(self, web_site, office_id):
        self.logger.debug("add web site {} ".format(web_site))
        assert web_site not in self.web_sites
        s = TDeclarationWebSite()
        s.calculated_office_id = office_id
        self.web_sites[web_site] = s

    def build_office_to_website(self):
        office_to_website = defaultdict(set)
        for url, web_site in self.web_sites.items():
            if TWebSiteReachStatus.can_communicate(web_site.reach_status) and url != 'declarator.org':
                office_to_website[web_site.calculated_office_id].add(url)
        return office_to_website

    def has_web_site(self, web_site):
        return web_site in self.web_sites

    def set_status_to_web_site(self, web_site, reach_status):
        assert TWebSiteReachStatus.check_status(reach_status)
        self.web_sites[web_site].reach_status = reach_status

    def get_web_site(self, web_site):
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
