import csv
import argparse
import logging
import csv


def setup_logging(logfilename="create_golden.log"):
    logger = logging.getLogger("golden")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser("Usage: %prog [options] input_tsv1 input_tsv2 ...")
    parser.add_argument('--negative-ratio', dest="negative_ratio", type=int,
                        help='try to delete negative cases to achieve the given ratio in percent \
                             for example --negative-ratio 50 means that the count of postives and negatives must the same' )
    parser.add_argument('--output-file', dest="output_file")
    parser.add_argument('input_files', nargs='+', help='input assignment files from toloka')
    args = parser.parse_args()
    return args


class TFileCollector:
    def __init__(self, negative_ratio):
        self.logger = setup_logging()
        self.tasks = list()
        self.negative_ratio = negative_ratio

    def collect_data(self, filename):
        self.logger.info("open file {}".format(filename))
        with open(filename, "r", encoding="utf-8") as tsv:
            for task in csv.DictReader(open(filename), delimiter="\t"):
                if task['INPUT:id_left'] == "" or task['INPUT:id_right'] == "":
                    continue  # skip empty lines
                task['GOLDEN:result'] = task['OUTPUT:result']
                task['HINT:text'] = task['OUTPUT:comments']
                self.tasks.append(task)

    def try_to_achieve_negative_ratio(self):
        if self.negative_ratio is None:
            return
        goal_negative_count = (float(self.negative_ratio) / 100.0) * len(self.tasks)
        negative_cnt = 0
        new_tasks = list()
        self.logger.info("goal_negative_count = {}".format(goal_negative_count))
        for t in self.tasks:
            if t['GOLDEN:result'].lower() == 'no':
                if negative_cnt < goal_negative_count:
                    new_tasks.append(t)
                negative_cnt += 1
            else:
                new_tasks.append(t)
        self.logger.info("delete {} negative cases to achieve positive/negative ratio".format(
            len(self.tasks) - len(new_tasks) ))
        self.tasks = new_tasks


    def write_output(self, output_filename):
        with open(output_filename, 'w') as csvfile:
            fieldnames = ['INPUT:id_left', 'INPUT:id_right',  'INPUT:json_left', 'INPUT:json_right', 'GOLDEN:result', 'HINT:text']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            for t in self.tasks:
                writer.writerow(t)


if __name__ == '__main__':
    args = parse_args()
    c = TFileCollector(args.negative_ratio)
    for f in args.input_files:
        c.collect_data(f)
    c.try_to_achieve_negative_ratio()
    c.write_output(args.output_file)

