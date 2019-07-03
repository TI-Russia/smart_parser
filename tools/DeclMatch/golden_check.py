import shutil
import sys
import os
from decl_match_metric import calc_decl_match_one_pair, trunctate_json, dump_conflict
import argparse
from multiprocessing import Pool
from collections import defaultdict
import json
import csv

DATA_FOLDER = "data"
if os.path.exists(DATA_FOLDER):
    shutil.rmtree(DATA_FOLDER)
os.mkdir(DATA_FOLDER)


#======================= copy data from drop box ========================
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toloka",  dest='toloka', help ="toloka assignments file")
    parser.add_argument("--golden-pool",  dest='golden_pool', help ="toloka golden pool (with jsons)")
    parser.add_argument("--dump-conflicts", dest='dump_conflicts')
    parser.add_argument("-l", dest='toloka_tsv_line_no', type=int, default=0)
    return parser.parse_args()


def avg(items):
    count = 0
    all_sum = 0.0
    for i in items:
        count += 1
        all_sum += i
    if count == 0:
        return -1

    return all_sum / count


class TTolokaStats:
    def __init__(self, args):
        self.args = args
        self.golden_pool = {}
        with open (args.golden_pool, "r", encoding="utf8") as tsv:
            for task in csv.DictReader(tsv, delimiter="\t", quotechar='"'):
                self.golden_pool[task["INPUT:input_id"]] = task['GOLDEN:declaration_json']

    def collect_stats(self, filename):
        line_no = 1 # header
        if args.dump_conflicts:
            conflict_file = open(args.dump_conflicts, "w", encoding="utf8")
        else:
            conflict_file = None
        global DATA_FOLDER
        decl_matches = []
        with open (filename, "r", encoding="utf8") as tsv:
            for task in csv.DictReader(tsv, delimiter="\t", quotechar='"'):
                line_no += 1
                task['input_line_no'] = line_no
                if args.toloka_tsv_line_no > 0 and args.toloka_tsv_line_no != line_no:
                    continue
                input_id = task["INPUT:input_id"]
                json_str = task['OUTPUT:declaration_json']
                if json_str == '':
                    print (input_id + " no json, skipped")
                    continue

                toloker_json = json.loads(json_str)
                golden_json = json.loads(self.golden_pool[input_id])
                with open(os.path.join(DATA_FOLDER, input_id+".toloker.json"), "w", encoding="utf8") as outf:
                    json.dump(toloker_json, outf, indent=4, ensure_ascii=False, sort_keys=True)
                with open(os.path.join(DATA_FOLDER, input_id+".golden.json"), "w", encoding="utf8") as outf:
                    json.dump(golden_json, outf, indent=4, ensure_ascii=False, sort_keys=True)
                match_info = calc_decl_match_one_pair(golden_json, toloker_json)
                if match_info.f_score != 1.0:
                    dump_conflict(task,golden_json, toloker_json, match_info, conflict_file)
                print (match_info.f_score)
                for e in match_info.dump_errors():
                    print (e)
                decl_matches.append(match_info.f_score)

        if args.dump_conflicts:
            conflict_file.close()
        print ("Avg decl_match:" + str(avg(decl_matches)) )


if __name__ == '__main__':
    args = parse_args()
    toloka_stats = TTolokaStats(args)
    toloka_stats.collect_stats (args.toloka)

