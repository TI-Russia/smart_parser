import shutil
import sys
import os
from decl_match_metric import calc_decl_match_one_pair
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
    parser.add_argument("--dump-conflicts", dest='dump_conflicts')
    parser.add_argument("-l", dest='toloka_tsv_line_no', type=int, default="None")
    return parser.parse_args()


def input_html_file_name(input_id):
    global DATA_FOLDER
    return os.path.join(DATA_FOLDER, input_id + ".html")

def smart_parser_result_json_file(input_id):
    htmlfile = input_html_file_name(input_id);
    return  htmlfile[:htmlfile.rfind('.')] + ".json"

def avg(items):
    count = 0
    all_sum = 0.0
    for i in items:
        count += 1
        all_sum += i
    return all_sum / count


def  add_html_table_row(cells):
    res = "<tr>"
    for c in cells:
        res  += "  <td"
        if c["MergedColsCount"] > 1:
            res += " colspan=" + str(c["MergedColsCount"])
        res += ">"
        res += c["Text"].replace("\n", '<br/>')
        res += "</td>\n"
    return res + "</tr>\n"


def convert_to_html(jsonStr, maintag="html"):
    data = json.loads(jsonStr)
    res = "<"+ maintag +">"
    res += "<h1>" +  data['Title'] + "</h1>\n"
    res += "<table border=1>\n"
    res += "<thead>\n"
    for r in  data["Header"]:
        res += add_html_table_row(r)
    res += "</thead>\n"
    res += "<tbody>\n"
    for r in  data["Section"]:
        res += add_html_table_row(r)
    for r in  data["Data"]:
        res += add_html_table_row(r)
    res += "</tbody>\n"
    res += "</table>"
    res += "</" + maintag + ">"
    return res;


def dump_conflict (task, match_info, conflict_file):
    global DATA_FOLDER
    input_id = task['INPUT:input_id']
    res = "<div>\n"
    res += "<table border=1> <tr>\n"

    res += "<tr>"
    res += "<td colspan=3><h1>"
    res += "f-score={}".format(match_info.f_score)
    res += " worker_id={}".format(task['ASSIGNMENT:worker_id'])
    res += " input_id={}".format(task['INPUT:input_id'])
    res += " line_no={}".format(task['input_line_no'])
    res += "</h1>"
    res += "</td></tr>"

    res += "<td width=30%>\n"

    input_json = task["INPUT:input_json"]
    res += convert_to_html(input_json, "div")
    res += "</td>\n"

    res += "<td width=30%>"
    res += "<textarea cols=80 rows=90>"
    res += json.dumps(json.loads(task["OUTPUT:declaration_json"]), indent=4, ensure_ascii=False)
    res += "</textarea>"
    res += "</td>\n"

    res += "<td>"
    res += "<textarea cols=80 rows=90>"
    with open (smart_parser_result_json_file(input_id), "r", encoding="utf8") as f:
        res += f.read()
    res += "</textarea>"
    res += "</td>\n"
    res += "</tr><tr>\n"
    res  += "<td colspan=3>"
    res += "<h1>"
    res += "f-score={}".format(match_info.f_score) + "<br/>"
    res += "<br/>".join(match_info.dump_errors())
    res += "</h1>"
    res += "\n</tr></table>"
    res  += "</td>"
    conflict_file.write(res)


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
                if args.toloka_tsv_line_no is not None and args.toloka_tsv_line_no != line_no:
                    continue
                task_id = task['INPUT:input_id']
                task['input_line_no'] = line_no
                if task["GOLDEN:declaration_json"] == "":
                    self.tasks[task_id].append (task)
                else:
                    self.golden_task_assignments += 1

    def calc_decl_match_for_tasks(self, input_id, conflict_file):
        json_file = smart_parser_result_json_file(input_id)
        if not os.path.exists(json_file):
            self.decl_match[input_id] = 0  #smart parser failed
            return
        automatic_json = json.load(open(json_file, encoding="utf8"))
        decl_matches = []

        for x in self.tasks[input_id]:
            toloker_json = json.loads(x['OUTPUT:declaration_json'])
            match_info = calc_decl_match_one_pair(toloker_json, automatic_json)
            decl_matches.append(match_info.f_score)
            match_info.dump(input_id, x['ASSIGNMENT:worker_id'], self.errors)

            toloka_json_file = json_file[:-5] + "." + x['ASSIGNMENT:worker_id'] + ".json"
            with open(toloka_json_file,"w", encoding="utf8") as outf:
                json.dump(toloker_json, outf, indent=4, ensure_ascii=False)
            if conflict_file:
                dump_conflict(x, match_info, conflict_file)
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
            filename = input_html_file_name(input_id)
            with open(filename, "w", encoding="utf8") as output_html:
                html = convert_to_html(input_json)
                output_html.write(html)

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

