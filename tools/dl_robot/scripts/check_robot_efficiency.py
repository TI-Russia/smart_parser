import re
from collections import defaultdict
import datetime
import argparse
import json
import matplotlib.pyplot as plt


class TTimeDistribution:
    def __init__(self):
        self.start_time = None
        self.engine = None
        self.time_stats = defaultdict(float)
        self.counts = defaultdict(int)

    def save_start_point(self, t, engine):
        self.update_last_time(t)
        self.engine = engine
        self.start_time = t

    def update_last_time(self, t):
        if self.engine is not None:
            self.counts[self.engine] += 1
            self.time_stats[self.engine] += (t - self.start_time).total_seconds()
            self.engine = None
            self.start_time = None

    def all_points_count(self):
        return sum (self.counts.values())

    def to_json(self):
        return dict( (
                         k,
                         {'seconds': int(v), 'count': self.counts[k]})
                     for k, v in self.time_stats.items())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-plot", dest='show_plot', required=False, action="store_true", default=False)
    parser.add_argument("logs", nargs='+')
    return parser.parse_args()


class TStats:
    def __init__(self, file_path):
        self.file_path = file_path
        self.urllib_find_links_count = 0
        self.urllib_request_head_count = 0
        self.exported_files_count = 0.0
        self.robot_step_count = 0
        self.engine_stats = TTimeDistribution()
        self.step_stats = TTimeDistribution()
        self.start_time = None
        self.end_time = None
        self.found_declarations = list()

    def analyze_dlrobot_log(self):
        with open(self.file_path) as inp:
            for line in inp:
                line = line.strip()
                items = line.split()
                # 2020-05-02 23:31:26,669
                try:
                    line_time = datetime.datetime.strptime(" ".join((items[0], items[1])), '%Y-%m-%d  %H:%M:%S,%f')
                except Exception as exp:
                    print ("cannot parse line {}, exception {}, keep going...".format(line, exp))
                    continue
                if self.start_time is None:
                    self.start_time = line_time
                self.end_time = line_time
                if line.find('find_links_in_html_by_text') != -1:
                    self.engine_stats.save_start_point(line_time, 'urllib')
                if line.find('find_links_with_selenium') != -1:
                    self.engine_stats.save_start_point(line_time, 'selenium')

                mo = re.match('.*=+ step ([^=]+) =+', line)
                if mo:
                    self.engine_stats.update_last_time(line_time)
                    self.robot_step_count += 1
                    step_name = mo.group(1)
                    self.step_stats.save_start_point(line_time, step_name)

                mo = re.match('.*urllib.request.urlopen.*method=([A-Z]+).*', line)
                if mo:
                    method = mo.group(1)
                    if method == "HEAD":
                        self.urllib_request_head_count += 1.0

                mo = re.match('.*exported\s+([0-9]+)\s+files.*', line)
                if mo:
                    self.exported_files_count = float(mo.group(1))
                if line.find('found a declaration') != -1:
                    self.found_declarations.append(line_time)

            self.engine_stats.update_last_time(self.end_time)
            self.step_stats.update_last_time(self.end_time)

    def all_seconds(self):
        return (self.end_time - self.start_time).total_seconds()

    # number declarations per minute
    def robot_speed(self):
        return round(60*self.exported_files_count / (self.all_seconds() + 0.00000001), 4)

    def get_stats(self):
        all_seconds = (self.end_time - self.start_time).total_seconds()
        return {
            'all_seconds': self.all_seconds(),
            'engine_time_stats': self.engine_stats.to_json(),
            'step_time_stats': self.step_stats.to_json(),
            "urllib_request_head": int(self.urllib_request_head_count),
            "exported_files": int(self.exported_files_count),
            "robot_steps":  self.robot_step_count,
            "robot_speed": self.robot_speed()
        }

    def get_speed_plot(self):
        x = list()
        y = list()
        cnt = 0
        for p in self.found_declarations:
            x.append(int((p - self.start_time).total_seconds()))
            #cnt = 0
            #for p1 in self.found_declarations:
            #    if p1 < p and int((p - p1).total_seconds()) < 60*10:
            #        cnt += 1
            cnt += 1
            y.append(cnt)
        return x,y


if __name__ == "__main__":
    args = parse_args()
    stats_list = list()
    for f in args.logs:
        stats = TStats(f)
        stats.analyze_dlrobot_log()
        stats_list.append(stats)
        print(json.dumps(stats.get_stats(), indent=4))

    if args.show_plot:
        plt.figure(1)
        plt.xlabel('Time')
        plt.ylabel('Found Declaration')
        plt.title('Robot Speed')
        for s in stats_list:
            x, y = s.get_speed_plot()
            plt.plot(x, y, label="{}, speed:{}".format(s.file_path, s.robot_speed()))
        plt.legend(loc='best')
        plt.show(block=True)