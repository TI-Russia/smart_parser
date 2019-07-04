import shutil
import sys
import os
from decl_match_metric import calc_decl_match_one_pair, trunctate_json, dump_conflict
import argparse
from multiprocessing import Pool
from collections import defaultdict
import signal
import json
import csv
import shutil

DATA_FOLDER = "data"
#======================= copy data from drop box ========================
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toloka",  dest='toloka', help ="toloka assignments file")
    parser.add_argument("--smart-parser", dest='smart_parser')
    parser.add_argument("--process-golden", action='store_true', default=False, dest="process_golden")
    parser.add_argument("--dump-conflicts", dest='dump_conflicts')
    parser.add_argument("-l", dest='toloka_tsv_line_no', type=int, default=0)
    return parser.parse_args()


def input_json_file_name(input_id):
    global DATA_FOLDER
    return os.path.join(DATA_FOLDER, input_id + ".toloka_json")

def smart_parser_result_json_file(input_id):
    infile = input_json_file_name(input_id);
    return  infile[:infile.rfind('.')] + ".json"

def avg(items):
    count = 0
    all_sum = 0.0
    for i in items:
        count += 1
        all_sum += i
    if count == 0:
        return -1
   
    return all_sum / count



def convert_automatic_json(data):
    for p in  data.get('persons', []):
        for i in p.get('incomes', []):
            i['size_raw'] =  i.pop('size')
    return data

class TTolokaStats:
    def __init__(self, args):
        self.tasks = defaultdict(list) # tasks wo golden
        self.golden_task_assignments = 0
        self.decl_match = {}
        self.errors = []
        self.args = args

    def collect_stats(self, filename):
        line_no = 1
        with open (filename, "r", encoding="utf8") as tsv:
            for task in csv.DictReader(tsv, delimiter="\t", quotechar='"'):
                line_no += 1
                if args.toloka_tsv_line_no > 0 and args.toloka_tsv_line_no != line_no:
                    continue
                task_id = task['INPUT:input_id']
                task['input_line_no'] = line_no
                if task.get("GOLDEN:declaration_json", "") == "" or args.process_golden:
                    self.tasks[task_id].append (task)
                else:
                    self.golden_task_assignments += 1


    def calc_decl_match_for_tasks(self, input_id, conflict_file):
        json_file = smart_parser_result_json_file(input_id)
        if not os.path.exists(json_file):
            self.decl_match[input_id] = 0  #smart parser failed
            return
        automatic_json = json.load(open(json_file, encoding="utf8"))
        automatic_json = convert_automatic_json(automatic_json);
        decl_matches = []

        for task in self.tasks[input_id]:
            toloker_json = json.loads(task['OUTPUT:declaration_json'])
            match_info = calc_decl_match_one_pair(toloker_json, automatic_json)
            decl_matches.append(match_info.f_score)
            if match_info.f_score == 1.0:
                continue

            worker_id = task.get('ASSIGNMENT:worker_id', "unknown");
            match_info.dump(input_id, worker_id, self.errors)

            toloka_json_file = json_file[:-5] + "." + worker_id + ".json"
            toloker_json_trunc = trunctate_json(toloker_json)
            automatic_json_trunc = trunctate_json(automatic_json)
            with open(toloka_json_file,"w", encoding="utf8") as outf:
                json.dump(toloker_json_trunc, outf, indent=4, ensure_ascii=False, sort_keys=True)
            with open(json_file+".trunc", "w", encoding="utf8") as outf:
                json.dump(automatic_json_trunc, outf, indent=4, ensure_ascii=False, sort_keys=True)

            if conflict_file:
                dump_conflict(task, toloker_json_trunc, automatic_json_trunc, match_info, conflict_file)
        self.decl_match[input_id] = avg(decl_matches)


    def process(self, args):
        if args.smart_parser is None:
            raise Exception("specify --smart-parser argument")
        self.automatic_jsons = {}
        global DATA_FOLDER
        if os.path.exists(DATA_FOLDER):
            shutil.rmtree(DATA_FOLDER)
        os.mkdir(DATA_FOLDER)
        for input_id, input_tasks in self.tasks.items():
            input_json = input_tasks[0]["INPUT:input_json"]
            filename = input_json_file_name(input_id)
            with open(filename, "w", encoding="utf8") as output_json:
                output_json.write(input_json)

        smart_parser = os.path.abspath(args.smart_parser)
        cmd = "{} -skip-relative-orphan -v debug  -adapter prod {} > log ".format(smart_parser, DATA_FOLDER);
        print (cmd)
        os.system(cmd)

        if args.dump_conflicts:
            conflict_file = open(args.dump_conflicts, "w", encoding="utf8")
        else:
            conflict_file = None

        for input_id, input_tasks in self.tasks.items():
            try:
                self.calc_decl_match_for_tasks(input_id, conflict_file)
            except:
                print ("cannot process {}".format(input_id))
                raise

        if args.dump_conflicts:
            conflict_file.close()


    def report(self):
        return {
            "Uniq not golden tasks": len(self.tasks),
            "Average overlap": avg (list(len(t) for t in self.tasks.values())),
            "Found assignments without golden": sum (list(len(t) for t in self.tasks.values())),
            "Average decl_match": avg (t for t in self.decl_match.values())
        }


if __name__ == '__main__':
    args = parse_args()
    toloka_stats = TTolokaStats(args)
    toloka_stats.collect_stats (args.toloka)
    toloka_stats.process(args)
    metrics = toloka_stats.report()
    print(json.dumps(metrics, indent=2))

    with open("errors.txt", "w") as outf:
        for e in toloka_stats.errors:
            outf.write(e + "\n")

