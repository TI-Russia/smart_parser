import json
import os
from common.primitives import get_site_domain_wo_www


class TDeclarationWebSite:
    def __init__(self):
        self.interactions = list()
        self.calculated_office_id = None

    def read_from_json(self, js):
        self.interactions = js['events']
        self.calculated_office_id = js['calc_office_id']
        return self

    def write_to_json(self):
        return {
            'events': self.interactions,
            'calc_office_id': self.calculated_office_id,
        }


class TDeclarationWebSites:
    disclosures_office_start_id = 20000

    def __init__(self, logger):
        self.web_sites = dict()
        self.logger = logger
        self.file_name = os.path.join(os.path.dirname(__file__), "../data/web_sites.json")

    def load_from_disk(self):
        with open(self.file_name, "r") as inp:
            for k, v in json.load(inp).items():
                self.web_sites[k] = TDeclarationWebSite().read_from_json(v)

    def add_web_site(self, web_site, office_id):
        self.logger.debug("add web site {} ".format(web_site))
        assert web_site not in self.web_sites
        s = TDeclarationWebSite()
        s.calculated_office_id = office_id
        self.web_sites[web_site] = s

    def has_web_site(self, web_site):
        return  web_site in self.web_sites

    def get_web_site(self, web_site):
        return self.web_sites.get(web_site)

    def save_to_disk(self):
        with open(self.file_name, "w") as outp:
            js = dict( (k, v.write_to_json()) for (k, v) in self.web_sites.items())
            json.dump(js, outp, indent=4, ensure_ascii=False)

    def add_new_websites_from_declarator(self, website_to_most_freq_office):
        for web_site, calculated_office_id in website_to_most_freq_office.items():
            if web_site not in self.web_sites:
                self.add_web_site(web_site, calculated_office_id)
            elif self.web_sites[web_site].calculated_office_id >= self.disclosures_office_start_id:
                raise Exception ("there is a web site {} that is referenced in "
                                 "disclosures offices and declarator offices. Solve office ambiguity".format(web_site))

    def update_from_office_urls(self, offices, logger):
        for o in offices:
            web_site = get_site_domain_wo_www(o.get('url'))
            if web_site not in self.web_sites:
                self.add_web_site(web_site, o['id'])
                logger.info ('add a website {} from office.url'.format(web_site))
