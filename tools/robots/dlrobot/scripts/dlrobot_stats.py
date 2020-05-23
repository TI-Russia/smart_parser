import argparse
import re
import plotly.express as px
import pandas as pd
import datetime
import os
from glob import glob
from pathlib import Path
import sys

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clicks-stats-glob", dest='clicks_stats_glob', required=False,
                        help="for example /home/sokirko/declarator_hdd/processed_projects.[0-9][0-9]/*/*.clicks.stats")
    parser.add_argument("--dlrobot-log-glob", dest='dlrobot_log_glob', required=False,
                        help="for example /home/sokirko/declarator_hdd/processed_projects.[0-9][0-9]/*/*.txt.log")
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


def process_clicks_stats(glob):
    declarations_count = []
    processed_files_count = []
    timestamps = []
    website = []
    sum_count = 0
    file_count = 0
    for mtime, value, file_name in get_click_stats_squeezes(glob):
        timestamps.append(pd.Timestamp(mtime))
        fname = os.path.basename(file_name)
        if fname.endswith(".txt.clicks.stats"):
            fname = fname[:-len(".txt.clicks.stats")]
        website.append(fname)
        sum_count += value
        file_count += 1
        declarations_count.append(sum_count)
        processed_files_count.append(file_count)

    df = pd.DataFrame({'Date': timestamps, "DeclarationCount": declarations_count, "website": website})
    fig = px.line(df, x='Date', y='DeclarationCount',
                        hover_data=["website"],
                        title='Declaration Crawling Progress')
    fig.write_html('declaration_crawling_stats.html')

    df = pd.DataFrame({'Date': timestamps, "FilesCount": processed_files_count, "website": website} )
    fig = px.line(df, x='Date', y='FilesCount',  title='File Progress', hover_data=["website"])
    fig.write_html('file_progress.html')


def get_time_stamp_from_log_line(log_line):
    time_stamp_str = " ".join(log_line.split(' ')[0:2])
    #2020-05-09 15:46:54,219
    date_time_obj = datetime.datetime.strptime(time_stamp_str, '%Y-%m-%d %H:%M:%S,%f')
    return date_time_obj


def get_dlrobot_log_squeezes(glob_pattern):
    files = glob(glob_pattern)
    result = []
    for f in files:
        try:
            with open(str(f), encoding="utf8") as inp:
                hostname = 'unknown'
                first_time_stamp = None
                last_not_empty_line = None
                exported_files_count = 0
                for line in inp:
                    m = re.search('hostname=(.*)\s*', line)
                    if m:
                        hostname = m.group(1)
                    if first_time_stamp is None:
                        first_time_stamp = get_time_stamp_from_log_line(line)
                    if len(line.strip()) != 0:
                        last_not_empty_line = line
                    mo = re.match('.*exported\s+([0-9]+)\s+files.*', line)
                    if mo:
                        exported_files_count = float(mo.group(1))

                last_time_stamp = get_time_stamp_from_log_line(last_not_empty_line)
                total_minutes = (last_time_stamp - first_time_stamp).total_seconds() / 60
                website = os.path.basename(f)
                if website.endswith(".txt.log"):
                    website = website[:-len(".txt.log")]
                result.append ((first_time_stamp, hostname, total_minutes, website, exported_files_count))
        except Exception as exp:
            print(exp)
            continue
        result.sort()
    return result


def process_dlrobot_logs(glob):
    minutes = []
    websites = []
    hostnames = []
    exported_files_counts = []
    start_time_stamps = []
    for start_time, host_name, total_minutes, website, exported_files_count in get_dlrobot_log_squeezes(glob):
        if total_minutes > 10:
            minutes.append(total_minutes)
            websites.append(website)
            hostnames.append(host_name)
            exported_files_counts.append(exported_files_count)
            start_time_stamps.append(start_time.strftime("%Y-%m-%d %H:%M:%S"))

    df = pd.DataFrame({'Minutes': minutes, "Websites": websites,
                       "hostnames": hostnames, "exported_files_counts": exported_files_counts,
                       'start_times': start_time_stamps})
    fig = px.line(df, x='start_times', y='Minutes',
                        hover_data=['Websites', "hostnames", "exported_files_counts", "start_times"],
                        title='Crawl Website Speed')
    fig.write_html('web_site_speed.html')



def main(args):
    if args.clicks_stats_glob is not None:
        process_clicks_stats(args.clicks_stats_glob)
    if args.dlrobot_log_glob is not None:
        process_dlrobot_logs(args.dlrobot_log_glob)


if __name__ == "__main__":
    args = parse_args()
    main(args)
    sys.exit(0)
