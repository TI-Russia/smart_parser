import os
import csv
import optparse
from collections import defaultdict, Counter


def parse_opts():
    optp = optparse.OptionParser("Usage: %prog [options] input_tsv1 input_tsv2 ...")
    optp.add_option('-u', '--output-unison-tsv', dest="output_unison_tsv")
    optp.add_option('-m', '--output-majority-vote-tsv', dest="output_majority_vote_tsv")
    optp.add_option('-f', '--fix-list', dest="fix_list", default=None)
    optp.add_option('-v', '--verbose', dest="verbose", default=0, type=int)
    optp.add_option('--input-folder', dest="input_folder", default=None)
    (opts, args) = optp.parse_args()
    if len(args) == 0:
        optp.error("incorrect number of arguments")
    return opts, args


# there is an answer with a majority vote
# YES, UNK, NO -> None
# YES YES ? -> YES
# NO NO ? -> NO
# UNK UNK ? -> UNK
def get_majority_vote(task_list):
    counts = Counter(x['OUTPUT:result'] for x in task_list)
    sorted_counts = sorted(((v, k) for k, v in counts.items()), reverse=True)
    if len(sorted_counts) == 1 or sorted_counts[0][0] > sorted_counts[1][0]:
        return sorted_counts[0][1]


# all answers are equal
def get_unison_vote(task_list):
    if len(set(x['OUTPUT:result'] for x in task_list)) == 1:
        return task_list[0]['OUTPUT:result']


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


class TToloker:
    def __init__(self):
        self.all_answers = 0
        self.golden_pass = 0
        self.golden_fail = 0

    def update(self, task):
        if task['GOLDEN:result'] != "":
            if task['OUTPUT:result'] == task['GOLDEN:result']:
                self.golden_pass += 1
            else:
                self.golden_fail += 1
        self.all_answers += 1


class TTolokaStats:
    def __init__(self, fixlist, verbose):
        self.tolokers = defaultdict(TToloker)
        self.tasks = defaultdict(list)  # tasks wo golden
        self.fixlist = fixlist
        self.verbose = verbose
        self.golden_task_assignments = 0

    def collect_stats(self, filename):
        with open(filename, "r", encoding="utf-8") as tsv:
            for task in csv.DictReader(open(filename), delimiter="\t"):
                if task['INPUT:id_left'] == "" or task['INPUT:id_right'] == "":
                    continue  # skip empty lines

                self.tolokers[task['ASSIGNMENT:worker_id']].update(task)

                task_id = task['INPUT:id_left'] + " " + task['INPUT:id_right']
                if task["GOLDEN:result"] == "":
                    self.tasks[task_id].append(task)
                else:
                    self.golden_task_assignments += 1

    def get_fixed_answer(self, id1, id2, answer):
        if id1 > id2:
            id1, id2 = id2, id1
        if id1 == id2:
            return (None, None, None)
        fixed_answer = self.fixlist.get((id1, id2), answer)
        return id1, id2, fixed_answer

    def write_tolokers_stats(self, aggr_fail, aggr_pass, name):
        rank_list = []
        for toloker_id, v in aggr_fail.items():
            toloker = self.tolokers[toloker_id]
            errors_count = (aggr_fail[toloker_id] + toloker.golden_fail)
            errors_rate = errors_count / float(toloker.all_answers)
            rank_list.append((errors_rate, toloker_id, errors_count))

        print("Bad tolokers for {}".format(name))
        errors_rate_sum = 0.
        for errors_rate, toloker_id, errors_count in sorted(rank_list, reverse=True):
            toloker = self.tolokers[toloker_id]
            errors_rate_sum += errors_rate
            if errors_count > 1 and errors_rate > 0.1:
                print("toloker= {} errors_rate={} all_errors={} golden_errors={} against_mv={} all_answers={}".format(
                    toloker_id, errors_rate, errors_count, toloker.golden_fail, aggr_fail[toloker_id],
                    toloker.all_answers))
        all_tolokers = set()
        all_tolokers.update(aggr_fail.keys())
        all_tolokers.update(aggr_pass.keys())
        all_tolokers_count = len(all_tolokers)
        print("Average Error Rate={}".format(errors_rate_sum / float(all_tolokers_count)))

    def write_aggregated_tsv(self, filename, aggregation):
        aggr_pass = defaultdict(int)
        aggr_fail = defaultdict(int)
        if filename is None:
            return
        with open(filename, "w", encoding="utf-8") as of:
            header = ["INPUT:id_left", "INPUT:id_right", "GOLDEN:result"]
            of.write("\t".join(header) + "\n")
            lines_count = 0
            fixed_count = 0
            for id, task_list in self.tasks.items():
                answer = aggregation(task_list)
                id1, id2, fixed_answer = self.get_fixed_answer(task_list[0]["INPUT:id_left"],
                                                               task_list[0]["INPUT:id_right"], answer)
                if fixed_answer is not None:
                    of.write("\t".join((id1, id2, fixed_answer)).strip() + "\n")
                    lines_count += 1
                    for task in task_list:
                        toloker = task['ASSIGNMENT:worker_id']
                        if task['OUTPUT:result'] == fixed_answer:
                            aggr_pass[toloker] += 1
                        else:
                            aggr_fail[toloker] += 1
                    if fixed_answer != answer:
                        fixed_count += 1

            print("write {} examples to {}".format(lines_count, filename))
            print("fixed examples via fixlist {}".format(fixed_count))

            self.write_tolokers_stats(aggr_fail, aggr_pass, aggregation.__name__)

    def get_fixed_answers_count(self):
        sum = 0
        for id, task_list in self.tasks.items():
            for task in task_list:
                id1, id2, answer = self.get_fixed_answer(task['INPUT:id_left'], task['INPUT:id_right'],
                                                         task['OUTPUT:result'])
                if answer != task['OUTPUT:result']:
                    sum += 1
        return sum

    def print_stats(self):
        task_answer_stats = defaultdict(int)
        for id, task_list in self.tasks.items():
            for task in task_list:
                task_answer_stats[task['OUTPUT:result']] += 1
        print("Input task answer stats: {}".format(task_answer_stats))
        print("Uniq not golden tasks: {}".format(len(self.tasks)))
        print("Average overlap: {}".format(mean(list(len(t) for t in self.tasks.values()))))
        print("Found assignments without golden: {}".format(sum(list(len(t) for t in self.tasks.values()))))
        print("Golden task assignments: {}".format(self.golden_task_assignments))
        print("Fixed assignments via fixlist: {}".format(self.get_fixed_answers_count()))


def read_fix_list(filename):
    if opts.fix_list is None:
        print("do not generate a production pool without fixlist.tsv and do not commit it!")
        return {}

    fix_list = {}
    possible_answers = ["YES", "NO", "UNK"]
    for l in open(filename):
        items = list(l.strip().split("\t"))
        if len(items) < 3:
            print("Error at line {}".format(l))
            assert (len(items) >= 3)
        id1 = items[0]
        id2 = items[1]
        m = items[2]
        if m not in possible_answers:
            print("Error at line {}".format(l))
            assert (m in possible_answers)
        if id1 > id2:
            id1, id2 = id2, id1
        fix_list[(id1, id2)] = m
    return fix_list


if __name__ == '__main__':
    opts, input_tsvs = parse_opts()
    fixlist = read_fix_list(opts.fix_list)
    stats = TTolokaStats(fixlist, opts.verbose)
    for input_tsv in input_tsvs:
        if opts.input_folder is not None:
            input_tsv = os.path.join(opts.input_folder, input_tsv)
        stats.collect_stats(input_tsv)

    stats.write_aggregated_tsv(opts.output_unison_tsv, get_unison_vote)
    stats.write_aggregated_tsv(opts.output_majority_vote_tsv, get_majority_vote)

    stats.print_stats()
