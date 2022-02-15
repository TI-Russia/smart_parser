import re
from common.primitives import normalize_whitespace
from common.russian_fio import TRussianFio


class TDeclarationTitleParser:
    def __init__(self, title):
        self.title = normalize_whitespace(title)
        self.input_title = title
        self.type = None
        self.decl_objects = list()
        self.decl_time = None
        self.declarant_positions = list()

    def find_starter(self):
        type_regexp = "^((Уточненные Сведения)|(Сведения)|(Справка)|(Информация)|(С В Е Д Е Н И Я))"
        match = re.search(type_regexp, self.title, re.IGNORECASE)
        if match is not None:
            self.type = self.title[:match.end()]
            self.title = self.title[match.end():].strip()
            match = re.search("(о|об)", self.title, re.IGNORECASE)
            if match is not None:
                self.title = self.title[match.end():].strip()
            return True
        return False

    def find_decl_objects(self):
        match = re.search("^ *(о|об) ", self.title, re.IGNORECASE)
        if match is not None:
            self.title = self.title[match.end():].strip()
        objects_regexps = r"^((доходах)|(расходах)|(имуществе)|(обязательствах имущественного характера))"
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

    #лиц, замещающих муниципальные должности и членов их семей администрации города Лысьвы за отчетный период с 1 января 2013 года по 31 декабря 2013 года.
    def find_declarant_position(self):
        r = '^(, )?представленные'
        match = re.search(r, self.title, re.IGNORECASE)
        if match is not None:
            self.title = self.title[match.end():].strip()
        words = self.title.split(" ")
        i = 0
        while i < len(words):
            if TRussianFio.is_morph_animative_noun(words[i].strip(', ')):
                offset = self.title.find(words[i]) + len(words[i])
                self.declarant_positions.append(self.title[:offset].strip(' ,'))
                self.title = self.title[offset:].strip()
                return True
            i += 1
            if i > 4:
                break
        return False

    def find_declarant_position_plus(self):
        for s in ["лиц, замещающих муниципальные должности"]:
            if self.title.startswith(s):
                self.declarant_positions.append(s)
                self.title = self.title[len(s):].strip(' ,')
                #if self.title.startswith("и "):
                #    self.title = self.title[2:]

    def find_time(self):
        time_regexps = [
            "за (отчетный )?период с [0-9]+ января [0-9]+ ?(года|г.) по [0-9]+ декабря [0-9]+ ?(года|г.)",
            "за (отчетный )?период с [0-9]+ января по [0-9]+ декабря [0-9]+ ?(года|г.)",
            "за (отчетный )?период с [0-9]+.[0-9]+.[0-9]+ по [0-9]+.[0-9]+.[0-9]+",
            "за [0-9]+ год"
        ]
        for r in time_regexps:
            match = re.search(r, self.title, re.IGNORECASE)
            if match is not None:
                self.decl_time =  self.title[match.start():match.end()].strip()
                self.title = self.title[:match.start()].strip()
                return True
        return False

    def delete_children(self):
        s = self.title.find('а также')
        if s == -1:
            s = self.title.find('его супруг')
            if s == -1:
                s = self.title.find('ее супруг')
        e = self.title.rfind('детей')
        if s != -1 and e != -1:
            self.title = self.title[:s].strip() + " " + self.title[e + len('детей'):].strip()
            self.title = self.title.strip(' ,')
            return

        r = [r"и членов (ее|его|их) сем..",
             ]
        for x in r:
            self.title = re.sub(x, "", self.title)

    def parse(self, raise_exception=False):
        self.find_starter()
        if not self.find_decl_objects():
            if raise_exception:
                raise Exception("cannot parse decl objects {}".format(self.title))
            else:
                return False
        if not self.find_declarant_position():
            if raise_exception:
                raise Exception("cannot parse declarant position {}".format(self.title))
            else:
                return False
        self.find_declarant_position_plus()
        if not self.find_time():
            if raise_exception:
                raise Exception("cannot parse declaration time  {}".format(self.title))
            else:
                return False
        self.delete_children()
        self.org_name = self.title.strip()
        return True

    def to_json(self):
        return {
            "input": self.input_title,
            "type": self.type,
            "objects": self.decl_objects,
            "time": self.decl_time,
            "positions": self.declarant_positions,
            "org_name": self.org_name
        }

    @staticmethod
    def from_json(j):
        r = TDeclarationTitleParser(j['input'])
        r.type = j['type']
        r.decl_objects = j['objects']
        r.decl_time = j['time']
        r.declarant_positions = j['positions']
        r.org_name = j['org_name']
        return r