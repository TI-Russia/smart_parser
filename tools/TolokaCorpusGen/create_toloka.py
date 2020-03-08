import shutil
import sys
import os
import random
import argparse
from hash_golden import hashGoldenTolokaFile

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-folder", dest='output_folder', required=True)
    parser.add_argument("--file-list", dest='file_list', default="_files.txt", help="a file to store declaration input file names")
    parser.add_argument("--toloka-output", dest='toloka_output')
    parser.add_argument("--toloka-golden", dest='toloka_golden', default="../../toloka/assignments/golden_1.tsv")
    return parser.parse_args()


def read_file_list(args):
    with open(args.file_list, "r") as file_list_stream:
        for filename in  file_list_stream:
            yield filename.strip()


def read_toloka_file_name(filename):
    lines = []
    filename = filename + ".toloka"
    if not os.path.exists(filename):
        return lines
    with open(filename, "r", encoding="utf8") as inpf:
        line_count = 0
        for x in  inpf:
            if line_count == 0:
                assert x.startswith("INPUT:input_id\tINPUT:input_json\tGOLDEN:declaration_json\tHINT:text")
            else:
                lines.append(x)
            line_count += 1
    return lines



if __name__ == '__main__':
    args = parse_args()
    golden_ratio = 0.10
    golden_file = list(hashGoldenTolokaFile(args.toloka_golden))
    golden = golden_file[1:]
    header = golden_file[0]
    random.shuffle(golden)
    main = []
    for f in read_file_list(args):
        main +=  read_toloka_file_name(f)

    if len(main) * golden_ratio > len(golden):
        new_main_len = int(len(golden) / golden_ratio)
        sys.stderr.write("not enough golden examples, truncate main examples to {}.. ".format(new_main_len))
        main = main[0 : new_main_len]

    if len(main) * golden_ratio < len(golden):
        new_golden_len = int(len(main) * golden_ratio)
        sys.stderr.write("not enough main examples, truncate golden to {} ... ".format(new_golden_len))
        golden = golden[0 : new_golden_len]
    new_corpus = main + golden
    random.shuffle(new_corpus)
    with open(args.toloka_output, "w", encoding="utf8") as outf:
        outf.write(header + "\n")
        for l in new_corpus:
            outf.write(l + "\n")


