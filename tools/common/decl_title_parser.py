import re
from common.primitives import normalize_whitespace
from common.russian_fio import TRussianFio
from office_db.russian_regions import TRussianRegions
from common.russian_morph_dict import TRussianDictWrapper


class TDeclarationTitleParser:
    def __init__(self, title):
        self.title = normalize_whitespace(title)
        self.input_title = title
        self.type = None
        self.decl_objects = list()
        self.decl_time = None
        self.declarant_positions = list()
        self.fio = None
        self.regions = TRussianRegions()
        self.region_name = None
        self.org_name = None

    def find_starter(self):
        for p in ['сведения о доходах']:
            i = self.title.lower().find(p)
            if i != -1:
                self.title = self.title[i:]
                break
        type_regexp = "^((Уточненные Сведения)|(Сведения)|(Справка)|(Информация)|(С В Е Д Е Н И Я))"
        match = re.search(type_regexp, self.title, re.IGNORECASE)
        if match is not None:
            self.type = self.title[:match.end()]
            self.title = self.title[match.end():].strip()
            match = re.search("^(о|об)", self.title, re.IGNORECASE)
            if match is not None:
                self.title = self.title[match.end():].strip()
            return True
        return False

    def to_json(self):
        return {
            "input": self.input_title,
            "type": self.type,
            "objects": self.decl_objects,
            "time": self.decl_time,
            "positions": self.declarant_positions,
            "org_name": self.org_name,
            "fio": self.fio,
            "region": self.region_name
        }

    @staticmethod
    def from_json(j):
        r = TDeclarationTitleParser(j['input'])
        r.type = j['type']
        r.decl_objects = j['objects']
        r.decl_time = j['time']
        r.declarant_positions = j['positions']
        r.org_name = j['org_name']
        r.fio = j.get('fio')
        r.region_name = j.get('region')
        return r

    def find_decl_objects(self):
        match = re.search("^ *(о|об) ", self.title, re.IGNORECASE)
        if match is not None:
            self.title = self.title[match.end():].strip()
        objs = ['доходах',
            'расходах',
            'имуществе',
            'обязательствах ?имущественного ?характера',
            'сведения ?об ?источниках ?получения ?средств',
                'источниках ?получения ?средств']
        objects_regexps = "^({})".format('|'.join(map(lambda x: "({})".format(x), objs)))
        match = re.search(objects_regexps, self.title, re.IGNORECASE)
        objects_cnt = 0
        while match is not None:
            objects_cnt += 1
            self.decl_objects.append(self.title[:match.end()].strip().lower())
            self.title = self.title[match.end():].strip()
            match = re.search("^(и|,)( (о|об))? ",  self.title, re.IGNORECASE)
            if match is not None:
                self.title = self.title[match.end():].strip()
            match = re.search(objects_regexps, self.title, re.IGNORECASE)
        return objects_cnt > 0

    #Сведения ведущий специалист комитета по ФК, спорту, туризму и молодёжной политике администрации Зеленчукского муниципального района Карачаево-Черкесской Республики, и членов его семьи за период с 1 января по 31 декабря 2011 года Беланова сергея Николаевича Декларированный годовой доход за 2011 г. (руб.) Перечень объектов недвижимого имущества и транспортных средств, принадлежащих на праве собственности Перечень объектов недвижимого имущества, находящихся в пользовании
    def find_declarant_position(self):
        self.find_declarant_position_const()
        r = '^(, )?представленные'
        match = re.search(r, self.title, re.IGNORECASE)
        if match is not None:
            self.title = self.title[match.end():].strip()
        words = self.title.split(" ")
        i = 0
        while i < len(words):
            w = words[i].strip(', ')
            if TRussianFio.can_start_fio(w):
                break
            if TRussianDictWrapper.is_morph_animative_noun(w) and w != "заместителя":
                offset = self.title.find(words[i]) + len(words[i])
                self.declarant_positions.append(self.title[:offset].strip(' ,'))
                self.title = self.title[offset:].strip()
                self.find_declarant_position_const()
                return True
            i += 1
            if i > 4:
                break
        return len(self.declarant_positions) > 0

    def find_fio_at_start(self):
        words = self.title.split(" ")
        if len(words) >= 3:
            if TRussianFio.is_fio_in_text(words[:3]):
                offset = self.title.find(words[2]) + len(words[2])
                self.fio = self.title[:offset].strip(' ,')
                self.title = self.title[offset:].strip()
                return True
        return False

    def find_fio_in_the_end(self):
        words = self.title.strip().split(" ")
        if len(words) >= 3:
            if TRussianFio.is_fio_in_text(words[-3:]):
                offset = self.title.find(words[-3])
                self.fio = self.title[offset:].strip(' ,')
                self.title = self.title[:offset].strip()
                return True
        return False

    def find_declarant_position_const(self):
        for s in ["лиц, замещающих муниципальные должности",
                  "лиц, замещающих муниципальные и выборные должности",
                  "лица, замещающего государственную должность",
                  "лиц, замещающих должности",
                  "лиц, замещающих должности государственной гражданской службы",
                  "представленные лицами, замещающими государственные должности",
                  "лицами, замещающими должности"
                  ]:
            if self.title.startswith(s):
                self.declarant_positions.append(s)
                self.title = self.title[len(s):].strip(' ,')
                region_id, start, end = self.regions.get_region_all_forms_at_start(self.title)
                if region_id is not None:
                    self.region_name = self.regions.get_region_by_id(region_id).name
                    self.title = self.title[end:].strip(' ,')
                if self.title.startswith('и '):
                    self.title = self.title[2:].strip(' ,')
                    if not self.find_declarant_position_const():
                        self.title = "и " + self.title
                return True
    #'СВЕДЕНИЯ о доходах, об имуществе и обязательствах имущественного характера лица, замещающего государственную должность Российской Федерации, Короткова Алексея Владимировича и членов его семьи'
    def find_time(self, search_everywhere=True):
        if self.decl_time is not None:
            return True
        time_starter = "за (отчетный )?(финансовый )?((период)|(год))"
        time_regexps = [
            time_starter + " с [0-9]+ января [0-9]+ ?(года|г.) по [0-9]+ декабря [0-9]+ ?(года|г.)",
            time_starter + " с [0-9]+ января по [0-9]+ декабря [0-9]+ ?(года|г.)",
            time_starter + " с [0-9]+.[0-9]+.[0-9]+ по [0-9]+.[0-9]+.[0-9]+",
            "за [0-9]+ год"
        ]
        for r in time_regexps:
            if not search_everywhere:
                r = "^({})".format(r)
            match = re.search(r, self.title, re.IGNORECASE)
            if match is not None:
                self.decl_time =  self.title[match.start():match.end()].strip()
                if search_everywhere:
                    self.title = self.title[:match.start()].strip()
                else:
                    self.title = self.title[match.end():].strip()
                return True
        return False

    def delete_unused(self):
        for p in ['а также', 'его супруг', 'ее супруг']:
            s = self.title.find(p)
            if s != -1:
                break
        for p in ['детей', 'ребенка']:
            e = self.title.rfind(p)
            if e != -1:
                e += len(p)
                break

        if s != -1 and e != -1:
            self.title = self.title[:s].strip() + " " + self.title[e:].strip()
            self.title = self.title.strip(' ,')
            return

        regexps = [r"и членов (ее|его|их) сем..",
             r"для размещения на официальном сайте и средствах массовой информации"
             ]
        for x in regexps:
            self.title = re.sub(x, "", self.title)

    def looks_like_orgname(self, orgname):
        starter = "^(структурно)|(территориал)"
        if re.search(starter, orgname, re.IGNORECASE) is None:
            return False
        ender = "((республики)|(области)|(края))$"
        if re.search(ender, orgname, re.IGNORECASE) is None:
            return False
        return True

    def parse(self, raise_exception=False):
        self.find_starter()
        if not self.find_decl_objects():
            if self.type is None:
                if raise_exception:
                    raise Exception("cannot parse decl objects {}".format(self.title))
                else:
                    return False
        self.find_time(search_everywhere=False)
        if not self.find_declarant_position():
            if not self.find_fio_at_start():
                if self.looks_like_orgname(self.title):
                    self.org_name = self.title
                    return True
                if raise_exception:
                    raise Exception("cannot parse declarant position {}".format(self.title))
                else:
                    return False
        else:
            self.find_fio_at_start()
        self.find_time()
        self.delete_unused()
        self.find_fio_in_the_end()
        self.org_name = self.title.strip(' ,')
        if self.org_name.startswith("в "):
            self.org_name = self.org_name[2:]
        return True


