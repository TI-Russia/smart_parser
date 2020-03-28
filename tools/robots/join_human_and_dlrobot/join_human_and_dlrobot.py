import shutil
import os
import argparse
import hashlib
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dlrobot-folder", dest='dlrobot_folder', default='dlrobot-folder')
    parser.add_argument("--human-json", dest='human_json', default="human_files.json")
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human.json")
    parser.add_argument("--skip-existing", dest='skip_existing', action="store_true", default=False)
    return parser.parse_args()


def build_sha256(filename):
    with open(filename, "rb") as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()


def process_domain(args, domain, human_json, dlrobot_json):
    print("process {}".format(domain))
    domain_folder = os.path.join(args.dlrobot_folder, domain)
    if not os.path.isdir(domain_folder):
        return
    domain_info = dict()
    new_files_found_by_dlrobot = 0
    files_count = 0
    for f in os.listdir(domain_folder):
        file_path = os.path.join(domain_folder, f)
        if file_path.endswith(".json") or file_path.endswith(".txt"):
            continue
        files_count += 1
        sha256 = build_sha256(file_path)
        if sha256 in human_json:
            domain_info[sha256] = human_json[sha256]
            human_json['dlrobot_found'] = True
        else:
            domain_info[sha256] = {
                "human_miss": True
            }
            new_files_found_by_dlrobot += 1
        domain_info[sha256]['dlrobot_path'] = f
    dlrobot_json[domain] = domain_info
    print("files: {},  new_files_found_by_dlrobot: {}".format(files_count, new_files_found_by_dlrobot))


def copy_human_file(args, sha256, file_info, dlrobot_json):
    if file_info.get('dlrobot_found', False) == True:
        return
    domain = file_info['domain']
    if domain == "":
        domain = "unknown_domain"
    folder = os.path.join(args.dlrobot_folder, domain)
    if not os.path.exists(folder):
        print("create {}".format(folder))
        os.mkdir(folder)
    infile = file_info['filepath']
    outfile = os.path.join(folder, "h" + os.path.basename(infile))
    if args.skip_existing and os.path.exists(outfile):
        print("skip copy {}, it exists".format(outfile))
    else:
        print("copy {} to {}".format(infile, outfile))
        if not os.path.exists(infile):
            print("Error! Cannot copy {}".format(infile))
        else:
            shutil.copyfile(infile, outfile)
    dlrobot_json.get(domain, dict())[sha256] = file_info


if __name__ == '__main__':
    args = parse_args()
    files = {}
    print  ("load {}".format(args.human_json))
    with open (args.human_json, "r") as inp:
        human_json = json.load(inp)
    dlrobot_json = dict()
    for domain in os.listdir(args.dlrobot_folder):
        try:
            process_domain(args, domain, human_json, dlrobot_json)
        except Exception as exp:
            print("Error on {}: {}, keep going".format(domain, exp))


    for sha256, file_info in human_json.items():
        try:
            copy_human_file(args, sha256, file_info, dlrobot_json)
        except Exception as exp:
            print("Error on {} : {}, keep going".format(sha256, exp))


    with open(args.output_json, "w") as out:
        json.dump(dlrobot_json, out, indent=4)
