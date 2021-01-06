import declarations.models as models
from django.core.management import BaseCommand
import logging
import os
import sys
from collections import defaultdict
from declarations.russian_fio import TRussianFio
from django.conf import settings
import re


def setup_logging(logfilename="bad_fio.log"):
    logger = logging.getLogger("bad_fio")
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if os.path.exists(logfilename):
        os.remove(logfilename)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging()

    def check_normal_Russian_name(self, s):
        if s.name_rank is not None and s.name_rank < 10000:
            return True

        if s.surname_rank is not None and s.surname_rank < 10000:
            return True

        name = s.person_name
        if name.find('(') != -1:
            name = name[:name.find('(')].strip()
        words = name.split(' ')

        relatives = {"супруг", "супруга", "сын", "дочь"}
        while len(words) > 0 and words[-1].lower() in relatives:
            words = words[0:-1]

        if len(words) >= 0 and re.search('^[0-9]+[.]\s*$', words[0]) is not None:
            words = words[1:]

        if len(words) >= 3 and words[0].title() == words[0] and words[1].title() == words[1] and \
                words[2].strip(',-').lower()[-3:] in {"вич", "вна", "мич", "ьич", "тич", "чна"}:
            #self.logger.debug("{} is a name by patronymic suffix".format(name))
            return True


        if len(words) >= 3 and words[-3].title() == words[-3] and words[-2].title() == words[-2] and \
                words[-1].strip(',-').lower()[-3:] in {"вич", "вна", "мич", "ьич", "тич", "чна"}:
            #self.logger.debug("{} is a name by patronymic suffix".format(name))
            return True

        name = " ".join(words)
        if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.]\s*$', name) is not None:
            #self.logger.debug("{} is a name by initials".format(name))
            return True

        # Иванов И.И.
        if re.search('^[А-Я][а-я]+\s+[А-Я]\s*[.]\s*[А-Я]\s*[.]', name) is not None:
            #self.logger.debug("{} is a name by initials".format(name))
            return True

        # И.И. Иванов
        if re.search('[А-Я]\s*[.]\s*[А-Я]\s*[.][А-Я][а-я]+$', name) is not None:
            #self.logger.debug("{} is a name by initials".format(name))
            return True


        return False

    def process_sections(self):
        self.logger.info("read sections")
        good = defaultdict(int)
        bad = defaultdict(int)
        sql = """
            select id, person_name, source_document_id, name_rank, surname_rank 
            from declarations_section
        """
        cnt = 0
        s  = models.Section.objects.get(id=2083901)
        self.check_normal_Russian_name(s)

        for s in models.Section.objects.raw(sql):
            if self.check_normal_Russian_name(s):
                good[s.source_document_id] += 1
            else:
                bad[s.source_document_id] += 1
                self.logger.debug ("section_id = {}, doc_id={}, bad person_name {}".format(
                    s.id, s.source_document_id, s.person_name))
            #if cnt > 100000:
            #    break
            cnt += 1
        sql = """
            select d.id  
            from declarations_source_document d  
            join declarations_section s on s.source_document_id=d.id 
            where s.id in (select section_id from declarations_realestate) 
            group by d.id 
            having count(s.id) > 1
        """
        docs_with_real_estate = set(d.id for d in models.Source_Document.objects.raw(sql))
        for doc_id, bad_cnt in bad.items():
            if bad_cnt + good[doc_id] > 1:
                self.logger.debug("doc_id={} bad = {}, good={}".format(doc_id, bad_cnt, good[doc_id]))
                if good[doc_id] * 5 < bad_cnt + good[doc_id] and doc_id not in docs_with_real_estate:
                    self.logger.debug("doc_id = {} is bad".format(doc_id))



    def handle(self, *args, **options):
        self.process_sections()


