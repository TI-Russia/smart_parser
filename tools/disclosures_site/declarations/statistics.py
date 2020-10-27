import declarations.models as models
from collections import defaultdict
import json
import os
import sys
from declarations.input_json import TIntersectionStatus


ALL_METRIC_NAMES = {
    'source_document_count': 'All source document count',
    'source_document_only_dlrobot_count': 'Source document count (only_dlrobot)',
    'source_document_only_human_count': 'Source document count (only_human)',
    'source_document_both_found_count': 'Source document count (both found)',
    'sections_count': 'All sections count',
    'sections_count_only_dlrobot': 'Sections (only_dlrobot)',
    'sections_count_both_found': 'Sections (both found)',
    'sections_dedupe_score_greater_0': 'Sections (dedupe_score > 0)',
    'person_count': 'People count'
}


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

    def check_statistics(self, prev, curr):
        def check_sum_metric_increase(values_to_sum):
            metric_str = "+".join(values_to_sum)
            sys.stderr.write("check {} increases...\n")
            old = sum(prev.metrics[x] for x in values_to_sum)
            new = sum(curr.metrics[x] for x in values_to_sum)
            if old > new:
                raise Exception("metric {} is less than in the last db ({} < {}) ".format(
                    metric_str, new, old))
        check_sum_metric_increase(["source_document_count"])
        check_sum_metric_increase(["sections_count"])
        check_sum_metric_increase(["person_count"])
        check_sum_metric_increase(['source_document_only_dlrobot_count', 'source_document_both_found_count'])
        check_sum_metric_increase(['source_document_only_human_count', 'source_document_both_found_count'])
        check_sum_metric_increase(["sections_dedupe_score_greater_0"])

    def add_current_statistics(self, crawl_epoch):
        stats = TDisclosuresStatistics(crawl_epoch)
        stats.build()
        if len(self.history) > 0:
            self.check_statistics(self.history[-1], stats)
        self.history.append(stats)

    def write_to_disk(self):
        l = list(h.save_to_json() for h in self.history)
        with open(self.file_path, "w") as outp:
            json.dump(l, outp,  indent=4, ensure_ascii=False)

    def get_last(self):
        if len(self.history) == 0:
            self.add_current_statistics(0)
        return self.history[-1]

    @staticmethod
    def get_metric_name(id):
        return ALL_METRIC_NAMES[id]
