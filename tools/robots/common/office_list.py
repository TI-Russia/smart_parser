from bs4 import BeautifulSoup
import json
import logging
from download import download_with_cache, get_site_domain_wo_www, get_all_sha256


def read_one_office_info(table_url):
    html, info = download_with_cache(table_url)
    soup = BeautifulSoup(html, 'html5lib')
    office_info = {}
    for text in soup.findAll('div', {"class": "text"}):
        for table in text.findChildren('table', recursive=True):
            for row in table.findChildren('tr'):
                if row.text.find('Web-адрес') != -1:
                    cells = list(row.findAll('td'))
                    url = cells[1].text
                    if url.find('mvd.ru'):
                        url = "https://" + u'мвд.рф'.encode('idna').decode('latin')
                    office_info['url'] = url

    return office_info


class TRobotProject:
    def __init__(self, filename):
        self.project_file = filename
        self.offices = list()
        self.human_files = list()

    def write_offices(self):
        with open(self.project_file, "w", encoding="utf8") as outf:
            outf.write(json.dumps(self.offices, ensure_ascii=False, indent=4))


    def read_office_list(self):
        self.offices = list()
        with open(self.project_file, "r", encoding="utf8") as inpf:
            self.offices =  json.loads(inpf.read())

    def create_office_listby_consulant_ru(self):
        html, info = download_html_with_urllib("https://www.consultant.ru/document/cons_doc_LAW_65443/")
        soup = BeautifulSoup(html, 'html5lib')
        offices = []
        for  l in soup.findAll('a'):
            words = l.text.split()
            if len(words) == 0:
                continue
            first_word = words[0]
            if first_word not in {u"Министерство", u"Федеральное", u"Федеральная", u"Главное", u"Управление", u"Государственная", u"Служба"}:
                continue
            url = l.attrs['href']
            if not url.startswith('http://www.consultant.ru'):
                url = 'http://www.consultant.ru' + url
            office_info = read_one_office_info(url)
            office_info['name'] = l.text.strip('\n ')
            self.offices.append(office_info)
        self.write_offices()

    def read_human_files(self, filename):
        self.human_files = list()
        with open(filename, "r", encoding="utf8") as inpf:
            self.human_files = json.load(inpf)

    def create_by_hypots(self, filename):
        self.offices = list()
        with open (filename, "r", encoding="utf8") as inpf:
            for x in inpf:
                url = x.strip()
                if len(url) == 0:
                    continue
                domain = "http://" + get_site_domain_wo_www(x.strip())
                office = {
                    "name": domain,
                    "external_hypot": url,
                    "morda": {
                        "links" : {
                            domain: {
                                "text": "",
                                "engine": "extenal"
                            }
                        }
                    }
                }
                self.offices.append(office)
        self.write_offices()

    def check_all_offices(self, page_collection_name):
        logger = logging.getLogger("dlrobot_logger")
        for o in self.offices:
            main_url = list(o['morda']['links'])[0]
            main_domain = get_site_domain_wo_www(main_url)
            logger.debug("check_recall for {}".format(main_domain))
            robot_sha256 = get_all_sha256(o, page_collection_name)
            files_count = 0
            found_files_count = 0
            for x in self.files:
                if len(x['domain']) > 0:
                    domain = get_site_domain_wo_www(x['domain'])
                    if domain == main_domain or main_domain.endswith(domain) or domain.endswith(main_domain):
                        for s in x['sha256']:
                            files_count += 1
                            if s not in robot_sha256:
                                logger.debug("{0} not found from {1}".format(s, json.dumps(x)))
                            else:
                                found_files_count += 1
            logger.info(
                "all human files = {}, human files found by dlrobot = {}".format(files_count, found_files_count))

    def del_old_info(self, step_name):
        for office_info in self.offices:
            if step_name in office_info:
                del (office_info[step_name])



