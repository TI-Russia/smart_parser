import shutil
import os
from decl_match_metric import calc_decl_match_one_pair, trunctate_json, dump_conflict
import argparse
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
        self.tasks = []
        self.tolokers = {}

    def read_tasks(self, filename):
        line_no = 1 # header
        with open (filename, "r", encoding="utf8") as tsv:
            for task in csv.DictReader(tsv, delimiter="\t", quotechar='"'):
                line_no += 1
                task['input_line_no'] = line_no
                if args.toloka_tsv_line_no > 0 and args.toloka_tsv_line_no != line_no:
                    continue
                if task.get('OUTPUT:declaration_json', '') == '':
                    print(task["INPUT:input_id"] + " no json, skipped")
                    continue
                self.tasks.append(task)

    def calc_decl_match(self):
        decl_matches = []
        tolokers_decl_match = defaultdict(list)
        for task in self.tasks:
            input_id = task["INPUT:input_id"]
            toloker_json = json.loads(task['OUTPUT:declaration_json'])
            golden_json = json.loads(self.golden_pool[input_id])
            match_info = calc_decl_match_one_pair(golden_json, toloker_json)
            task['match_info'] = match_info
            print (match_info.f_score)
            for e in match_info.dump_errors():
                print (e)
            decl_matches.append(match_info.f_score)
            tolokers_decl_match[task['ASSIGNMENT:worker_id']].append (match_info.f_score)

        for t in tolokers_decl_match:
            self.tolokers[t] =  {'avg':avg(tolokers_decl_match[t]), 'tasks': len(tolokers_decl_match[t])}

        print ("Avg decl_match:" + str(avg(decl_matches)))


    def report(self):
        if args.dump_conflicts:
            conflict_file = open(args.dump_conflicts, "w", encoding="utf8")
        else:
            conflict_file = None
        global DATA_FOLDER
        for task in self.tasks:
            match_info = task['match_info']
            if match_info.f_score == 1.0:
                continue

            input_id = task["INPUT:input_id"]
            toloker_json = json.loads(task['OUTPUT:declaration_json'])
            golden_json = json.loads(self.golden_pool[input_id])
            with open(os.path.join(DATA_FOLDER, input_id+".toloker.json"), "w", encoding="utf8") as outf:
                json.dump(toloker_json, outf, indent=4, ensure_ascii=False, sort_keys=True)
            with open(os.path.join(DATA_FOLDER, input_id+".golden.json"), "w", encoding="utf8") as outf:
                json.dump(golden_json, outf, indent=4, ensure_ascii=False, sort_keys=True)
            dump_conflict(task, golden_json, toloker_json, match_info, conflict_file)

        if args.dump_conflicts:
            conflict_file.close()

        for t in self.tolokers:
            print (t + ": " + str(self.tolokers[t]))


if __name__ == '__main__':
    args = parse_args()
    toloka_stats = TTolokaStats(args)
    toloka_stats.read_tasks(args.toloka);
    toloka_stats.calc_decl_match()
    toloka_stats.report()

