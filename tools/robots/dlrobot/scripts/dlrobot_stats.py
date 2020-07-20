import argparse
import re
import plotly.express as px
import pandas as pd
import datetime
import os
from glob import glob
from pathlib import Path
import sys
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clicks-stats-glob", dest='clicks_stats_glob', required=False,
                        help="for example /home/sokirko/declarator_hdd/processed_projects.[0-9][0-9]/*/*.clicks.stats")
    parser.add_argument("--dlrobot-log-glob", dest='dlrobot_log_glob', required=False,
                        help="for example /home/sokirko/declarator_hdd/processed_projects.[0-9][0-9]/*/*.txt.log")
    parser.add_argument("--conversion-server-stats", dest='conversion_server_stats', required=False,
                        help="for example /home/sokirko/declarator_hdd/declarator/convert_stats.txt")
    args = parser.parse_args()
    return args


def get_click_stats_squeezes(clicks_stats_glob):
    files = glob(clicks_stats_glob)
    result = []
    for f in files:
        try:
            with open(str(f), encoding="utf8") as inp:
                m = re.search('"files_count": ([0-9]+),', inp.read())
                if m:
                    files_count = int(m.group(1))
                    mtime = datetime.datetime.fromtimestamp(Path(f).stat().st_mtime)
                    result.append((mtime,  files_count, str(f)))
                else:
                    continue
        except Exception as exp:
            print(exp)
            continue
    result.sort()
    return result


def build_html(fig, output_file):
    fig.write_html(output_file, include_plotlyjs='cdn')


class TClicksStatistics:
    def __init__(self, click_stats_squeezes, min_date=None):
        self.declarations_count = []
        self.processed_files_count = []
        self.timestamps = []
        self.website = []
        self.sum_count = 0
        self.file_count = 0
        for mtime, value, file_name in click_stats_squeezes:
            if min_date is not None and mtime < min_date:
                continue
            self.timestamps.append(pd.Timestamp(mtime))
            fname = os.path.basename(file_name)
            if fname.endswith(".txt.clicks.stats"):
                fname = fname[:-len(".txt.clicks.stats")]
            self.website.append(fname)
            self.sum_count += value
            self.file_count += 1
            self.declarations_count.append(self.sum_count)
            self.processed_files_count.append(self.file_count)

    def write_declaration_crawling_stats(self, html_file):
        df = pd.DataFrame({'Date': self.timestamps, "DeclarationCount": self.declarations_count, "website": self.website})
        fig = px.line(df, x='Date', y='DeclarationCount',
                      hover_data=["website"],
                      title='Declaration Crawling Progress')
        build_html(fig, html_file)

    def write_file_progress(self, html_file):
        df = pd.DataFrame({'Date': self.timestamps, "FilesCount": self.processed_files_count, "website": self.website})
        fig = px.line(df, x='Date', y='FilesCount', title='File Progress', hover_data=["website"])
        build_html(fig, html_file)


def process_clicks_stats(glob):
    click_stats_squeezes = get_click_stats_squeezes(glob)
    stats = TClicksStatistics(click_stats_squeezes)
    stats.write_declaration_crawling_stats('declaration_crawling_stats.html')
    stats.write_file_progress('file_progress.html')

    min_time = datetime.datetime.now() - datetime.timedelta(hours=12)
    stats = TClicksStatistics(click_stats_squeezes, min_time)
    stats.write_declaration_crawling_stats('declaration_crawling_stats_12h.html')
    stats.write_file_progress('file_progress_12h.html')


def get_time_from_log_line(log_line):
    time_stamp_str = " ".join(log_line.split(' ')[0:2])
    #2020-05-09 15:46:54,219
    date_time_obj = datetime.datetime.strptime(time_stamp_str, '%Y-%m-%d %H:%M:%S,%f')
    return date_time_obj


def build_log_squeeze(filename):
    with open(filename, encoding="utf8") as inp:
        hostname = 'unknown'
        first_time = None
        last_not_empty_line = None
        exported_files_count = 0
        for line in inp:
            m = re.search('hostname=(.*)\s*', line)
            if m:
                hostname = m.group(1)
            if first_time is None:
                first_time = get_time_from_log_line(line)
            if len(line.strip()) != 0:
                last_not_empty_line = line
            mo = re.match('.*exported\s+([0-9]+)\s+files.*', line)
            if mo:
                exported_files_count = float(mo.group(1))
        last_time = get_time_from_log_line(last_not_empty_line)
        total_minutes = (last_time - first_time).total_seconds() / 60
        website = os.path.basename(filename)
        if website.endswith(".txt.log"):
            website = website[:-len(".txt.log")]
        return {
            'first_time_stamp': first_time.timestamp(),
            'host_name': hostname,
            'total_minutes': total_minutes,
            'website': website,
            'exported_files_count': exported_files_count
        }


def get_dlrobot_log_squeezes(glob_pattern):
    files = glob(glob_pattern)
    result = []
    for f in files:
        try:
            filename = str(f)
            cached_squeeze_file_name = filename + ".squeeze_for_stats"
            if os.path.exists(cached_squeeze_file_name):
                with open(cached_squeeze_file_name, encoding="utf8") as inp:
                    squeeze = json.load(inp)
            else:
                squeeze = build_log_squeeze(str(f))
                with open(cached_squeeze_file_name, "w", encoding="utf8") as out:
                    json.dump(squeeze, out)
            result.append(squeeze)
        except Exception as exp:
            print(exp)
            continue
        result.sort(key=lambda x: x['first_time_stamp'])
    return result


def process_dlrobot_logs(glob):
    minutes = []
    websites = []
    host_names = []
    exported_files_counts = []
    start_time_stamps = []
    for squeeze in get_dlrobot_log_squeezes(glob):
        start_time = datetime.datetime.fromtimestamp( squeeze['first_time_stamp'])
        if squeeze['total_minutes'] > 10:
            minutes.append(squeeze['total_minutes'])
            websites.append(squeeze['website'])
            host_names.append(squeeze['host_name'])
            exported_files_counts.append(squeeze['exported_files_count'])
            start_time_stamps.append(start_time.strftime("%Y-%m-%d %H:%M:%S"))

    df = pd.DataFrame({'Minutes': minutes, "Websites": websites,
                       "hostnames": host_names, "exported_files_counts": exported_files_counts,
                       'start_times': start_time_stamps})
    fig = px.line(df, x='start_times', y='Minutes',
                        hover_data=['Websites', "hostnames", "exported_files_counts", "start_times"],
                        title='Crawl Website Speed')
    build_html(fig, 'web_site_speed.html')


def process_convert_stats(history_filename):
    with open(history_filename, encoding="utf8") as inp:
        timestamps = list()
        ocr_pending_all_file_sizes = list()
        for l in inp:
            (timestamp, stats) = l.split("\t")
            dttime = datetime.datetime.fromtimestamp(int(timestamp))
            timestamps.append(pd.Timestamp(dttime))
            ocr_pending_all_file_sizes.append( json.loads(stats)['ocr_pending_all_file_size'])

    df = pd.DataFrame({'Time': timestamps, "ocr_pending_file_sizes": ocr_pending_all_file_sizes})
    fig = px.line(df, x='Time', y='ocr_pending_file_sizes',
                        title='Ocr Conversion Server')
    output_file = os.path.join(os.path.dirname(history_filename), "ocr_pending_file_sizes.html")
    build_html(fig, output_file)


def main(args):
    if args.clicks_stats_glob is not None:
        process_clicks_stats(args.clicks_stats_glob)
    if args.dlrobot_log_glob is not None:
        process_dlrobot_logs(args.dlrobot_log_glob)
    if args.conversion_server_stats is not None:
        process_convert_stats(args.conversion_server_stats)


if __name__ == "__main__":
    args = parse_args()
    main(args)
    sys.exit(0)
