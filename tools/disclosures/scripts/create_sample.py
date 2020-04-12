import json
import os
import random
import glob

def add_files(sample_file, files):
    with open(sample_file, "r", encoding="utf8") as inp:
        for x in json.load(inp):
            if len(x['archive_files']) != 0:
                for i, f in enumerate(x['archive_files']):
                    _, file_extension = os.path.splitext(f)
                    files.append ("{}_{}.*".format(x['id'], i))
            else:
                _, file_extension = os.path.splitext(x['file'])
                files.append("{}.*".format(x['id']))


files = list()
add_files("parser-job-priority-1.json", files)
add_files("parser-job-priority-2.json", files)
random.shuffle(files)
folder = "sample"
sample_size = 1000

os.mkdir(folder)
files_count = 0

for filename in files:
    for  f in glob.glob( os.path.join("out.documentfile", filename)):
        os.system("cp {} {}".format(f, folder))
        files_count += 1
        if files_count >= sample_size:
            break
    if files_count >= sample_size:
        break

os.system("tar cf sample.tar {}".format(folder))