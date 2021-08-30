from common.logging_wrapper import setup_logging
from common.access_log import get_human_requests
import declarations.models as models

from django.core.management import BaseCommand
from collections import defaultdict
import os
import re
import json
import datetime


class TAccessLogReader:
    def __init__(self, logger, options):
        self.logger = logger
        self.options = options
        self.start_access_log_date = self.options.get('start_access_log_date')
        self.last_access_log_date = self.options.get('last_access_log_date')
        self.access_log_folder = self.options.get('access_log_folder')
        self.min_request_freq = self.options.get('self.min_request_freq', 3)

    def check_date(self, filename):
        (_, date_str, _) = filename.split('.')
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')

        if self.start_access_log_date is not None:
            if dt < datetime.datetime.strptime(self.start_access_log_date, '%Y-%m-%d'):
                self.logger.debug("skip {}, it is older than {}".format(filename, self.start_access_log_date))
                return False

        if self.last_access_log_date is not None:
            if dt > datetime.datetime.strptime(self.last_access_log_date, '%Y-%m-%d'):
                self.logger.debug("skip {}, it is newer than {}".format(filename, self.last_access_log_date))
                return False
        return True

    def build_popular_site_pages(self):
        self.logger.info("build_popular_site_pages")
        requests = defaultdict(int)
        processed_files_count = 0
        for x in os.listdir(self.access_log_folder):
            if not x.startswith('access'):
                continue
            if not self.check_date(x):
                continue
            processed_files_count += 1
            full_path = os.path.join(self.access_log_folder, x)
            for r in get_human_requests(full_path, http_status=200):
                match = re.match('^/(section|person)/([0-9]+)/?$', r)
                if match:
                    rec = (match[1].lower(), int(match[2]))
                    requests[rec] += 1
        self.logger.info("processed {} access log files".format(processed_files_count))
        filtered_by_min_freq = 0
        output_path = self.options['output_path']
        self.logger.info("write squeeze to {}".format(output_path))
        with open(output_path, "w") as outp:
            for (record_type, record_id), freq in requests.items():
                if freq < self.min_request_freq:
                    filtered_by_min_freq += 1
                    continue
                record = {
                    'record_id': record_id,
                    'record_type': record_type,
                    'req_freq': freq
                }
                outp.write("{}\n".format(json.dumps(record, ensure_ascii=False)))
        self.logger.info("filtered_by_min_freq({}) = {}".format(self.min_request_freq, filtered_by_min_freq))


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--access-log-folder",
            dest='access_log_folder',
            default="/home/sokirko/declarator_hdd/Yandex.Disk/declarator/nginx_logs/")

        parser.add_argument(
            "--start-access-log-date",
            dest='start_access_log_date',
            default=None,
            help="for example 2021-08-05"
        )

        parser.add_argument(
            "--last-access-log-date",
            dest='last_access_log_date',
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
        reader = TAccessLogReader(logger, options)
        reader.build_popular_site_pages()

AccessLogSqueezer=Command