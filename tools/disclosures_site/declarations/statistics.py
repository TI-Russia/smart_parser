import declarations.models as models
from collections import defaultdict
import json
import os
import sys
from declarations.input_json import TIntersectionStatus
from django.db import connection


ALL_METRIC_NAMES = {
    'source_document_count': 'All source document count',
    'source_document_only_dlrobot_count': 'Source document count (only_dlrobot)',
    'source_document_only_human_count': 'Source document count (only_human)',
    'source_document_both_found_count': 'Source document count (both found)',
    'sections_person_name_income_year_declarant_income_size': 'Count distinct (person_name, income_year, declarant_income_size)',
    'sections_person_name_income_year_spouse_income_size': 'Count distinct (person_name, income_year, spouse_income_size)',
    'sections_dedupe_score_greater_0': 'Sections (dedupe_score > 0)',
    'person_count': 'People count',
    'sections_count': 'All sections count',
    'sections_count_only_dlrobot': 'Sections (only_dlrobot)',
    'sections_count_both_found': 'Sections (both found)'
}


def sections_person_name_income_year_declarant_income_size(relative_code):
    query = """
        select count(distinct s.person_name, s.income_year, i.size) 
            from declarations_section s 
            join declarations_income i on s.id=i.section_id 
            where i.relative='{}'
    """.format(relative_code)
    with connection.cursor() as cursor:
        cursor.execute(query)
        for count, in cursor:
            return count


class TDisclosuresStatistics:
    def __init__(self, crawl_epoch=None):
        self.metrics = defaultdict(int)
        self.crawl_epoch = crawl_epoch

    def build(self):
        self.metrics['source_document_count'] = models.Source_Document.objects.all().count()
        self.metrics['source_document_only_dlrobot_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.only_dlrobot).count()
        self.metrics['source_document_only_human_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.only_human).count()
        self.metrics['source_document_both_found_count'] = models.Source_Document.objects.filter(intersection_status=TIntersectionStatus.both_found).count()

        self.metrics['sections_count'] = models.Section.objects.all().count()
        self.metrics['sections_count_only_dlrobot'] = models.Section.objects.filter(
            source_document__intersection_status=TIntersectionStatus.only_dlrobot).count()
        self.metrics['sections_count_both_found'] = models.Section.objects.filter(
            source_document__intersection_status=TIntersectionStatus.both_found).count()

        self.metrics['sections_person_name_income_year_declarant_income_size'] = \
            sections_person_name_income_year_declarant_income_size(models.Relative.main_declarant_code)
        self.metrics['sections_person_name_income_year_spouse_income_size'] = \
            sections_person_name_income_year_declarant_income_size(models.Relative.spouse_code)
        self.metrics['sections_dedupe_score_greater_0'] = models.Section.objects.filter(
            dedupe_score__gt=0).count()
        self.metrics['person_count'] = models.Person.objects.all().count()

    def save_to_json(self):
        return {
            "crawl_epoch" : self.crawl_epoch,
            "metrics":  self.metrics
        }

    def load_from_json(self, js):
        self.crawl_epoch = js['crawl_epoch']
        self.metrics = defaultdict()
        self.metrics.update(js['metrics'])


class TDisclosuresStatisticsHistory:
    def __init__(self):
        self.file_path = os.path.join(os.path.dirname(__file__), '../data/statistics.json')
        self.history = self.read_from_disk()

    def read_from_disk(self):
        result = list()
        if os.path.exists(self.file_path):
            with open(self.file_path) as inp:
                for h in json.load(inp):
                    stats = TDisclosuresStatistics()
                    stats.load_from_json(h)
                    result.append(stats)
        return result

    def check_sum_metric_increase(self, curr_unknown, values_to_sum):
        last_good = self.get_last()
        metric_str = "+".join(values_to_sum)
        sys.stderr.write("check {} increases...\n".format(metric_str))
        old = sum(last_good.metrics[x] for x in values_to_sum)
        new = sum(curr_unknown.metrics[x] for x in values_to_sum)
        if old > new:
            raise Exception("Fail! metric value {} is less than in the last db ({} < {}) ".format(
                metric_str, new, old))
        sys.stderr.write("success: {} <= {}\n".format(old, new))

    def check_statistics(self,  curr):
        self.check_sum_metric_increase(curr, ["source_document_count"])
        self.check_sum_metric_increase(curr, ['sections_person_name_income_year_declarant_income_size'])
        self.check_sum_metric_increase(curr, ['sections_person_name_income_year_spouse_income_size'])
        self.check_sum_metric_increase(curr, ["person_count"])
        self.check_sum_metric_increase(curr, ['source_document_only_dlrobot_count', 'source_document_both_found_count'])
        self.check_sum_metric_increase(curr, ['source_document_only_human_count', 'source_document_both_found_count'])
        self.check_sum_metric_increase(curr, ["sections_dedupe_score_greater_0"])
        # metrics sections_count, sections_count_only_dlrobot, sections_count_both_found can decrease
        # because we make progress in finding section copies. Metric sections_dedupe_score_greater_0 can fall also
        # but we have not seen it.

    @staticmethod
    def build_current_statistics(crawl_epoch):
        stats = TDisclosuresStatistics(crawl_epoch)
        stats.build()
        return stats

    def add_statistics(self, stats):
        self.history.append(stats)

    def write_to_disk(self):
        l = list(h.save_to_json() for h in self.history)
        with open(self.file_path, "w") as outp:
            json.dump(l, outp,  indent=4, ensure_ascii=False)

    def get_last(self):
        if len(self.history) == 0:
            stats = self.build_current_statistics(0)
            self.add_statistics(stats)
        return self.history[-1]

    @staticmethod
    def get_metric_name(id):
        return ALL_METRIC_NAMES[id]
