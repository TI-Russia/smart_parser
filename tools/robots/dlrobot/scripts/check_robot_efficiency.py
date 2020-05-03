import re
import sys
from collections import defaultdict
import datetime

class TTimeStatis:
    def __init__(self):
        self.start_time = None
        self.engine = None
        self.time_stats = defaultdict(float)

    def save_start_point(self, t, engine):
        self.update_last_time(t)
        self.engine = engine
        self.start_time = t

    def update_last_time(self, t):
        if self.engine is not None:
            self.time_stats[self.engine] += (t - self.start_time).total_seconds()
            self.engine = None
            self.start_time = None


if __name__ == "__main__":
    if len(sys.argv) == 1:
        input_stream = sys.stdin
    else:
        input_stream = open(sys.argv[1])
    urllib_find_links_count = 0
    selenium_find_links_count = 0
    urllib_request_head_count = 0
    urllib_request_get_count = 0
    exported_files_count = 0.0
    robot_step_count = 0
    engine_stats = TTimeStatis()
    step_stats = TTimeStatis()
    start_time = None
    end_time = None
    for line in input_stream:
        line = line.strip()
        if not line.startswith('2020-'):
            continue
        items = line.split()
        #2020-05-02 23:31:26,669
        line_time = datetime.datetime.strptime(" ".join((items[0], items[1])), '%Y-%m-%d  %H:%M:%S,%f')
        if start_time is None:
            start_time = line_time
        end_time = line_time
        urllib_find_links = line.find('find_links_in_html_by_text') != -1
        if urllib_find_links:
            urllib_find_links_count += 1.0
            engine_stats.save_start_point(line_time, 'urllib')
        selenium_find_links = line.find('find_links_with_selenium') != -1
        if selenium_find_links:
            selenium_find_links_count += 1.0
            engine_stats.save_start_point(line_time, 'selenium')

        mo = re.match('.*=+ step ([^=]+) =+', line)
        if mo:
            engine_stats.update_last_time(line_time)
            robot_step_count += 1
            step_name = mo.group(1)
            step_stats.save_start_point(line_time, step_name)

        urllib_request = mo = re.match('.*urllib.request.urlopen.*method=([A-Z]+).*', line)
        if mo:
            method = mo.group(1)
            if method == "HEAD":
                urllib_request_head = True
                urllib_request_head_count += 1.0
            if method == "GET":
                urllib_request_get = True
                urllib_request_get_count += 1.0

        mo = re.match('.*exported\s+([0-9]+)\s+files.*', line)
        if mo:
            exported_files_count = float(mo.group(1))
    engine_stats.update_last_time(end_time)
    step_stats.update_last_time(end_time)
    print('All milliseconds:{}'.format((end_time-start_time).total_seconds()))
    print ('Engine time stats:{}'.format(engine_stats.time_stats))
    print ('Step time stats:{}'.format(step_stats.time_stats))
    print ("urllib_find_links={}, selenium_find_links={}".format(urllib_find_links_count, selenium_find_links_count))
    print ("urllib_request_head={}, urllib_request_get={}".format(urllib_request_head_count, urllib_request_get_count))
    print ("exported_files={}".format(exported_files_count))
    print ("robot_steps={}".format(robot_step_count))

    page_fetched_count = urllib_find_links_count + selenium_find_links_count + 0.0000000001
    print ("robot efficiency={:.4f}".format(exported_files_count / page_fetched_count))
    if len(sys.argv) > 1:
        input_stream.close()
