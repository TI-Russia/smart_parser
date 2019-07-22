import argparse
from collections import Counter, defaultdict
import csv



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toloka",  dest='toloka', help ="toloka assignments file")
    parser.add_argument("--aggr-func",  dest='aggr_func', help ="maj_vote or unison", default="maj_vote")
    parser.add_argument("--output-pool",  dest='output_pool', help ="output pool")
    return parser.parse_args()


def get_majority_vote(task_list):
    counts = Counter(x['OUTPUT:declaration_hashcode'] for x in task_list)
    if len(counts) == 1:
        return task_list[0]
    sorted_counts = sorted( ((v,k) for k,v in counts.items()), reverse=True )
    if sorted_counts[0][0] == sorted_counts[1][0]:
        return None # two equal votes to different result
    for task in  task_list:
        if task['OUTPUT:declaration_hashcode'] == sorted_counts[0][1]:
            return task
    assert False


# all answers are equal
def get_unison_vote(task_list):
    if len(set(x['OUTPUT:declaration_hashcode'] for x in task_list)) == 1:
        return task_list[0]



class TTolokaStats:
    def __init__(self, args):
        self.args = args
        self.tasks = defaultdict(list)

    def read_tasks(self, filename):
        line_no = 1 # header
        #INPUT:input_id	INPUT:input_json	OUTPUT:declaration_json	OUTPUT:declaration_hashcode	GOLDEN:declaration_json	GOLDEN:declaration_hashcode	HINT:text	ASSIGNMENT:link	ASSIGNMENT:assignment_id	ASSIGNMENT:worker_id	ASSIGNMENT:status	ASSIGNMENT:started	ACCEPT:verdict	ACCEPT:comment

        with open (filename, "r", encoding="utf8") as tsv:
            for task in csv.DictReader(tsv, delimiter="\t", quotechar='"'):
                line_no += 1
                task['input_line_no'] = line_no
                if task.get('OUTPUT:declaration_json', '') == '':
                    print(task["INPUT:input_id"] + " no json, skipped")
                    continue
                if task.get('GOLDEN:declaration_hashcode', '') != '':
                    continue # skip golden
                self.tasks[task['INPUT:input_id']].append(task)

    def write_aggregated_tsv(self, filename, aggregation):
        if filename is None:
            return
        with open(filename, "w", encoding="utf8") as of:
            header = ["INPUT:input_id", "INPUT:input_json", "OUTPUT:declaration_json"]
            of.write("\t".join(header) + "\n")
            lines_count = 0
            for task_list in self.tasks.values():
                answer = aggregation(task_list)
                if answer == None:
                    continue
                lines_count += 1
                items = [answer["INPUT:input_id"], answer["INPUT:input_json"], answer["OUTPUT:declaration_json"]]
                of.write("\t".join(items) + "\n")

            print ("write {} examples to {}".format(lines_count, filename))



if __name__ == '__main__':
    args = parse_args()
    toloka_stats = TTolokaStats(args)
    toloka_stats.read_tasks(args.toloka);
    aggr_func = get_unison_vote if args.aggr_func == "unison" else get_majority_vote
    toloka_stats.write_aggregated_tsv(args.output_pool, aggr_func)

