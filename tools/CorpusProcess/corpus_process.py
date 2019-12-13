import shutil
import sys
import os
import time
import argparse
from multiprocessing import Pool
import signal
import json


# ======================= copy data from drop box ========================
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be copy_data, process, report or full", default='full')
    parser.add_argument("--output-folder", dest='output_folder', required=True)
    parser.add_argument("--file-list", dest='file_list', default="_files.txt",
                        help="a file to store declaration input file names")
    parser.add_argument("--dropbox-folder", dest='dropbox_folder')
    parser.add_argument("--smart-parser", dest='smart_parser')
    parser.add_argument("--smart-parser-options", dest='smart_parser_options',
                        default="-v debug -max-rows 100 -adapter prod -converted-storage-url  http://declarator.zapto.org:8000/converted_document")
    parser.add_argument("--toloka", dest='toloka', default=False, action="store_true")
    parser.add_argument("--process-count", dest='parallel_pool_size', help="run smart parser in N parallel processes",
                        default=4, type=int)
    parser.add_argument("-e", dest='extensions', default=[], action='append',
                        help="extensions: doc, docx, pdf, xsl, xslx, take all extensions if  this argument is absent")

    return parser.parse_args()


def check_extension(filename, all_extension):
    if all_extension is None:
        return True
    for x in all_extension:
        if filename.endswith(x):
            return True
    return False


def copy_data(args):
    if args.dropbox_folder is None:
        raise Exception("specify --dropbox-folder argument")
    if os.path.exists(args.output_folder):
        shutil.rmtree(args.output_folder)
    os.mkdir(args.output_folder)
    file_count = 0
    with open(args.file_list, "w") as file_list_stream:
        for root, dirs, files in os.walk(args.dropbox_folder):
            for f in files:
                if check_extension(f, args.extensions):
                    rel_path = os.path.relpath(root, args.dropbox_folder)
                    if rel_path == ".":
                        output_folder = args.output_folder
                    else:
                        output_folder = os.path.join(args.output_folder, rel_path)

                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)
                    input_file = os.path.join(root, f)
                    output_file = os.path.join(output_folder, f)
                    shutil.copy(input_file, output_file)
                    output_file = output_file.replace("\\", "/")
                    file_list_stream.write(output_file + "\n")
                    file_count += 1

    print("{0} files copied to {1}".format(file_count, args.output_folder))


# ======================= run smart_parser ========================
def read_file_list(args):
    with open(args.file_list, "r") as file_list_stream:
        for filename in file_list_stream:
            filename = filename.strip()
            if check_extension(filename, args.extensions):
                yield filename


def kill_process_windows(pid):
    os.system("taskkill /F /T /PID " + str(pid))


def fix_encoding(line):
    return line.encode('utf8', 'ignore').decode('utf8')


class ProcessOneFile(object):
    def __init__(self, args, parent_pid):
        self.args = args
        self.parent_pid = parent_pid

    def __call__(self, filename):
        smart_parser = os.path.abspath(self.args.smart_parser)
        log = filename + ".stdout"
        toloka_arg = " -toloka \"{}.toloka\" ".format(filename) if self.args.toloka else ""
        print(self.args.smart_parser_options)
        cmd = "{} -license lic.bin {} {} \"{}\" > \"{}\" ".format(smart_parser, toloka_arg, self.args.smart_parser_options, filename,
                                                 log)
        print(fix_encoding(cmd))
        try:
            os.system(cmd)
        except KeyboardInterrupt:
            kill_process_windows(self.parent_pid)


def process(args):
    if args.smart_parser is None:
        raise Exception("specify --smart-parser argument")

    filenames = read_file_list(args)
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = Pool(args.parallel_pool_size)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = pool.map(ProcessOneFile(args, os.getpid()), filenames)
    except KeyboardInterrupt:
        print("stop processing...")
        pool.terminate()
    else:
        pool.close()


# ======================= report ========================
class TCorpusFile:
    def __init__(self, sourcefile):
        self.SourceFile = sourcefile
        s = sourcefile + ".json"
        self.JsonFile = s if os.path.exists(s) else None
        if self.JsonFile is None:
            s = sourcefile + "_0.json"
            self.JsonFile = s if os.path.exists(s) else None
        self.SourceFileSize = os.path.getsize(self.SourceFile)


def check_json(fileName):
    data = json.load(open(fileName, encoding="utf8"))
    return len(data.get('persons', []))  > 0


def report(args):
    processed_files = []
    for f in read_file_list(args):
        processed_files.append(TCorpusFile(f))

    jsons_count = 0
    all_size = 0
    good_size = 0
    for x in processed_files:
        all_size += x.SourceFileSize
        if x.JsonFile is not None and check_json(x.JsonFile):
            jsons_count += 1
            good_size += x.SourceFileSize

    processed_files = sorted(processed_files, key=lambda x: x.SourceFileSize, reverse=True)
    errors = open("errors.txt", "w")
    for x in processed_files:
        if x.JsonFile is None:
            errors.write(x.SourceFile + " " + str(x.SourceFileSize) + "\n")

    return {
        "All found logs": len(processed_files),
        "All found jsons": jsons_count,
        "Source file size": all_size,
        "Source file with jsons size": good_size,
        "header_recall": round(good_size / all_size, 2)
    }


if __name__ == '__main__':
    args = parse_args()
    if not args.extensions:
        args.extensions = ['doc', 'docx', 'pdf', 'xls', 'xlsx']

    if args.action == 'full' or args.action == 'copy_data':
        copy_data(args)

    if args.action == 'full' or args.action == 'process':
        process(args)

    if args.action == 'full' or args.action == 'report':
        metrics = report(args)
        print(json.dumps(metrics, indent=2))
