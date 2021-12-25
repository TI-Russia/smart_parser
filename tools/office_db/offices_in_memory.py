from office_db.rubrics import TOfficeRubrics, RubricsInRussian, TOfficeProps
from office_db.russian_regions import TRussianRegions
from office_db.declaration_office_website import TDeclarationWebSite
from common.urllib_parse_pro import TUrlUtf8Encode, urlsplit_pro

import json
import os
import re


class TOfficeInMemory:

    def __init__(self, office_id=None, name=None, parent_id=None, type_id=None, rubric_id=None, region_id=None,
                 address=None, wikidata_id=None, office_web_sites=None):
        self.office_id = office_id
        self.name = name
        self.parent_id = parent_id
        self.type_id = type_id
        self.rubric_id = rubric_id
        self.region_id = region_id
        self.address = address
        self.wikidata_id = wikidata_id
        self.office_web_sites = list()
        if office_web_sites is not None:
            self.office_web_sites = office_web_sites

    def from_json(self, js):
        self.office_id = int(js['id'])
        self.name = js['name']
        self.parent_id = js['parent_id']
        self.type_id = js['type_id']
        self.rubric_id = js.get('rubric_id')
        self.region_id = js['region_id']
        self.address = js.get('address')
        self.wikidata_id = js.get('wikidata_id')
        self.office_web_sites = list( TDeclarationWebSite().read_from_json(x) for x in js.get('urls', list()))
        return self

    def to_json(self):
        rec = {
            'id': self.office_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'type_id': self.type_id,
            'rubric_id': self.rubric_id,
            'region_id': self.region_id
        }
        if self.address is not None:
            rec['address'] = self.address
        if self.wikidata_id is not None:
            rec['wikidata_id'] = self.wikidata_id
        if len(self.office_web_sites) > 0:
            rec['urls'] = list(x.write_to_json() for x in self.office_web_sites)
        return rec

    def add_web_site(self, site_url: str):
        # russian domain must be in utf8
        assert not TUrlUtf8Encode.is_idna_string(site_url)
        assert site_url.startswith("http")
        for x in self.office_web_sites:
            assert x.url != site_url
        s = TDeclarationWebSite()
        s.url = site_url
        self.office_web_sites.append(s)

    @property
    def urls_html(self):
        site_info: TDeclarationWebSite
        hrefs = list()
        for site_info in self.office_web_sites:
            p = urlsplit_pro(site_info.url)
            anchor = p.netloc + p.path
            if not site_info.can_communicate():
                href = "{} (obsolete)".format(anchor)
            else:
                href = '<a href="{}">{}</a>'.format(site_info.url, anchor)
            hrefs.append(href)
        return ";&nbsp;&nbsp;&nbsp;".join(hrefs)

    @property
    def wikidata_url_html(self):
        if self.wikidata_id is None:
            return ''
        id = self.wikidata_id
        return "<a href=\"https://www.wikidata.org/wiki/{}\">{}</a>".format(id, id)


class TOfficeTableInMemory:
    SELECTED_OFFICES_FOR_TESTS = None
    group_types = set([10, 12, 16, 17]) # these offices do not exist like all Moscow courts

    def go_to_the_top(self, office_id):
        cnt = 0
        while True:
            cnt += 1
            if cnt > 5:
                raise Exception("too deep structure, probably a cycle found ")
            if self.offices[office_id].parent_id is None:
                return office_id
            parent: TOfficeInMemory
            parent = self.offices[self.offices[office_id].parent_id]
            if self.use_office_types:
                if parent.type_id in TOfficeTableInMemory.group_types:
                    return office_id
            office_id = parent.office_id
        return office_id

    def get_top_parent_office_id(self, office_id):
        return self.transitive_top[int(office_id)]

    def get_immediate_parent_office_id(self, office_id):
        if office_id is None:
            return None
        return self.offices[int(office_id)].parent_id

    def __init__(self, use_office_types=True):
        self.use_office_types = use_office_types
        self.offices = dict()
        self.transitive_top = dict()
        self.fsin_by_region = dict()

    def _init_special(self):
        for office_id in self.offices:
            self.transitive_top[office_id] = self.go_to_the_top(office_id)

        office_info: TOfficeInMemory
        main_fsin_office_id = 482
        for office_id, office_info in self.offices.items():
            if office_info.parent_id == main_fsin_office_id:
                self.fsin_by_region[office_info.region_id] = office_id
        self.fsin_by_region[TRussianRegions.Russia_as_s_whole_region_id] = main_fsin_office_id

    def get_office_id_to_ml_office_id(self):
        return list((i, o) for i, o in enumerate(self.offices))

    # echo  "select *  from declarations_office" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator data/offices.txt
    # echo  "select * from declarator.declarations_office  where id not in (select id from disclosures_db.declarations_office)" |  mysqlsh --sql --result-format=json/array --uri=declarator@localhost -pdeclarator -D declarator > offices.txt

    def read_from_local_file(self, filepath=None):
        if  filepath is None:
            filepath = os.path.join(os.path.dirname(__file__), "../office_db/data/offices.txt")
        with open(filepath) as inp:
            offices = json.load(inp)
            for o in offices:
                office_id = int(o['id'])
                if TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS is not None:
                    if office_id not in TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS:
                        continue
                self.offices[office_id] = TOfficeInMemory().from_json(o)
        if TOfficeTableInMemory.SELECTED_OFFICES_FOR_TESTS is None:
            self._init_special()

    def write_to_local_file(self, file_path):
        with open(file_path, "w") as outp:
            offices = list(x.to_json() for x in self.offices.values())
            json.dump(offices, outp, indent=4, ensure_ascii=False)

    def add_office(self, office: TOfficeInMemory):
        self.offices[str(office.office_id)] = office

    def read_from_table(self, table):
        for o in table:
            self.offices[o.id] = TOfficeInMemory(
                 office_id=o.id,
                 name=o.name,
                 parent_id=o.parent_id,
                 type_id=o.type_id,
                 rubric_id=o.rubric_id,
                 region_id=o.region_id
            )
        self._init_special()

    def _get_all_rubrics(self, office_id):
        all_rubrics = set()
        pattern = TOfficeProps(
            self.offices[office_id].name,
            top_parent=self.get_top_parent_office_id(office_id),
            immediate_parent=self.get_immediate_parent_office_id(office_id))

        for rubric in RubricsInRussian.keys():
            if pattern.check_rubric(rubric):
                all_rubrics.add(rubric)
        return all_rubrics

    def set_rubrics(self, logger):
        for o in self.offices.values():
            o.rubric_id = self.build_office_rubric(logger, o.office_id)

    def build_office_rubric(self, logger, office_id):
        rubrics = self._get_all_rubrics(office_id)
        office: TOfficeInMemory
        office = self.offices[office_id]
        parent_id = office.parent_id
        if len(rubrics) == 0 and parent_id is not None:
            rubrics = self._get_all_rubrics(parent_id)

        office_name = office.name
        if len(rubrics) > 1 and TOfficeRubrics.ExecutivePower in rubrics:
            rubrics.remove(TOfficeRubrics.ExecutivePower)
        rubric = None
        if len(rubrics) == 0:
            if logger is not None:
                logger.error("cannot find rubric for {} set Other".format(office_name))
            rubric = TOfficeRubrics.Other
        elif len(rubrics) == 1:
            rubric = list(rubrics)[0]
            if logger is not None:
                logger.debug("{} => {}".format(office_name, RubricsInRussian[rubric]['name']))
        elif TOfficeRubrics.Education in rubrics:
            rubrics = {TOfficeRubrics.Education}
            rubric = list(rubrics)[0]
            if logger is not None:
                logger.debug("{} => {}".format(office_name, RubricsInRussian[rubric]['name']))
        else:
            rubric_strs = list(RubricsInRussian[r]['name'] for r in rubrics)
            if logger is not None:
                logger.error("ambiguous office {} rubrics:{} ".format(office_name, ",".join(rubric_strs)))
        return rubric

    @staticmethod
    def convert_municipality_to_education(section_position):
        if section_position is None:
            return False
        heavy_position = re.search('(завуч|учитель|учительница)', section_position, re.IGNORECASE)  is not None
        light_position = re.search('(директор|заведующая|директора)', section_position, re.IGNORECASE) is not None
        schools = 'СОШ|СШ|МКОУ|МБУДО|МАОУ|ГБОУ|МОУ|колледж|ВСОШ|общеобразовательного|образовательным|школы|интерната'
        edu_office = re.search(schools, section_position) is not None
        return heavy_position or (light_position and edu_office)
