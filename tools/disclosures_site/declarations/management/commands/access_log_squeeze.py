from common.logging_wrapper import setup_logging
from common.access_log import get_human_requests
import declarations.models as models

from django.core.management import BaseCommand
from collections import defaultdict
import os
import re
import json


def get_id_and_sql_table(url_path):
    url_path = url_path.strip('/')
    if url_path.startswith('section/'):
        section_id = url_path[len('section/'):]
        if section_id.isdigit():
            return int(section_id), models.Section
    elif url_path.startswith('person/'):
        person_id = url_path[len('person/'):]
        if person_id.isdigit():
            return int(person_id), models.Person
    return None, None


class TAccessLogReader:
    def __init__(self, logger, access_log_folder, max_access_log_date, min_request_freq):
        self.logger = logger
        self.access_log_folder = access_log_folder
        self.max_access_log_date = max_access_log_date
        self.min_request_freq = min_request_freq

    def build_popular_site_pages(self, output_path):
        self.logger.info("build_popular_site_pages")
        requests = defaultdict(int)
        for x in os.listdir(self.access_log_folder):
            if x.startswith('access'):
                path = os.path.join(self.access_log_folder, x)
                if self.max_access_log_date is not None:
                    (_, date_str, _) = x.split('.')
                    dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    if dt > datetime.datetime.strptime(max_access_log_date, '%Y-%m-%d'):
                        self.logger.info("skip {}, it is newer than {}".format(x, self.max_access_log_date))
                        continue
                for r in get_human_requests(path):
                    if re.match('^/(section|person)/[0-9]+/?$', r):
                        r = r.rstrip('/')
                        requests[r] += 1

        filtered_by_min_freq = 0
        self.logger.info("write squeeze to {}".format(output_path))
        with open(output_path, "w") as outp:
            for request, freq in requests.items():
                if freq < self.min_request_freq:
                    filtered_by_min_freq += 1
                    continue
                id, model_type = get_id_and_sql_table(request)
                assert id is not None
                record = {
                    'record_id': id,
                    'record_type': ('section' if model_type == models.Section else "person"),
                    'req_freq': freq
                }
                 outp.write("{}\n".format(json.dumps(record, ensure_ascii=False))
        self.logger.info("filtered_by_min_freq({}) = {}".format(self.min_request_freq, filtered_by_min_freq))


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            "--access-log-folder",
            dest='access_log_folder',
            default="/home/sokirko/declarator_hdd/Yandex.Disk/declarator/nginx_logs/")

        parser.add_argument(
            "--max-access-log-date",
            dest='max_access_log_date',
            default=None,
            help="for example 2021-08-05"
        )

        parser.add_argument(
            "--min-request-freq",
            dest='min_request_freq',
            default=3,
            help="min freq in access logs"
        )

        parser.add_argument(
            "--output-path",
            dest='output_path',
        )

    def handle(self, *args, **options):
        logger = setup_logging(log_file_name="access_log_reader.log")
        reader = TAccessLogReader(logger, options['access_log_folder'], options['max_access_log_date'],
                                  options['min_request_freq'])
        reader.build_popular_site_pages(options['output_path'])