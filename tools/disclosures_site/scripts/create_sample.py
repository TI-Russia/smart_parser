import json
import os
import random
import glob
import argparse
import shutil


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-json",  dest='file_jsons', required=False,  action="append", help="parser-job-priority-1.json")
    parser.add_argument("--output-folder", dest='output_folder', default='sample')
    parser.add_argument("--human-files-folder", dest='human_files_folder', default='human_files')
    parser.add_argument("--sample-size", dest='sample_size', default=1000, type=int)
    return parser.parse_args()


def add_file_globs(sample_file, files):
    with open(sample_file, "r", encoding="utf8") as inp:
        for x in json.load(inp):
            if len(x['archive_files']) != 0:
                for i, f in enumerate(x['archive_files']):
                    _, file_extension = os.path.splitext(f)
                    files.append ("{}_{}.*".format(x['id'], i))
            else:
                _, file_extension = os.path.splitext(x['file'])
                files.append("{}.*".format(x['id']))


def get_sample_by_priority_files(args):
    file_globs = list()
    for f in args.file_jsons:
        add_file_globs("parser-job-priority-1.json", file_globs)

    random.shuffle(file_globs)

    files_count = 0

    for file_glob in file_globs:
        for f in glob.glob(os.path.join(args.human_files_folder, file_glob)):
            shutil.copy(f, args.output_folder)
            files_count += 1
            if files_count >= args.sample_size:
                break
        if files_count >= args.sample_size:
            break


def get_sample_by_all_human_files(args):
    files = list(x for x in os.listdir(args.human_files_folder) if not x.endswith(".zip"))
    sample = random.sample(files, args.sample_size)
    for f in sample:
        shutil.copy(os.path.join(args.human_files_folder, f), args.output_folder)


def main():
    args = parse_args()
    if os.path.exists(args.output_folder):
        print ("delete output folder{}, if you do not need it")
        return
    os.mkdir(args.output_folder)
    if args.file_jsons is None:
        get_sample_by_all_human_files(args)
    else:
        get_sample_by_priority_files(args)

    os.system("tar cf sample.tar {}".format(args.output_folder))

if __name__ == "__main__":
    main()
