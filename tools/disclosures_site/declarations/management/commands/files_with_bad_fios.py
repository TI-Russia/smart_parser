import declarations.models as models
from common.primitives import string_contains_Russian_name
from common.logging_wrapper import setup_logging

from django.core.management import BaseCommand
from collections import defaultdict


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.logger = setup_logging(logger_name="bad_fio.log")


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
            good_name = False
            if s.name_rank is not None and s.name_rank < 10000:
                good_name = True
            elif s.surname_rank is not None and s.surname_rank < 10000:
                good_name = True
            elif:
                good_name = string_contains_Russian_name(s)

            if good_name:
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


