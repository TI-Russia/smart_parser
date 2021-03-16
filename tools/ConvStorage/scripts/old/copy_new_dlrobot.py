from common.primitives import  build_dislosures_sha256_by_file_data

import glob
import os
import argparse
import hashlib
import json 
import shutil


TMPDIR = "tmp"
assert os.path.exists(TMPDIR)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob-pattern", dest='glob_pattern', default='./files/*.pdf')
    parser.add_argument("--convert-db-json", dest='convert_db_json')
    parser.add_argument("--dest-folder", dest='dest_folder')
    parser.add_argument("--dest-folder-for-ocr", dest='dest_folder_for_ocr')
    parser.add_argument("--dest-folder-for-winword", dest='dest_folder_for_winword')
    return parser.parse_args()


def check_pdf_has_text(filename):
    cmd = "pdftotext {0} dummy.txt".format(filename)
    print (cmd )
    os.system(cmd)
    return os.path.getsize("dummy.txt") > 200


def strip_drm_or_copy_original(filename, stripped_file):
    cmd = "pdfcrack {0} > crack.info".format(filename)
    print (cmd )
    os.system(cmd)
    password = None
    with open("crack.info", "r") as log:
        prefix = "found user-password: " 
        for l in log:
            if l.startswith(prefix):
                password = prefix[len(prefix):].strip("'");
    if password != None:
        print( "use password {0}".format(password))
        cmd = "qpdf --password={0} --decrypt {1} {2}".format(password, filename, stripped_file)
        print (cmd)
        os.system(cmd)
    else:
        shutil.copyfile(filename, stripped_file)


if __name__ == '__main__':
    args = parse_args()
    all_files = glob.glob(args.glob_pattern)
    convert_db_json = {}
    if args.convert_db_json is not None:
        with open(args.convert_db_json, "r", encoding="utf8") as inp:
            convert_db_json = json.load(inp)

    print("found {0} input files".format(len(all_files)))
    processed_files = {}
    for some_file in all_files:
        try:
            sha256hash = build_dislosures_sha256_by_file_data(some_file)

            if sha256hash in processed_files:
                print ("skip " + some_file + " already found in the input files ")
                continue

            if sha256hash in convert_db_json:
                print ("skip " + some_file + " already found in the convert_db_json")
                continue

            output_file_base_name  = sha256hash + os.path.splitext(some_file)[1]
            output_file_name  = os.path.join(args.dest_folder, output_file_base_name)
            print ("copy file " + some_file + " to " + output_file_name)
            shutil.copyfile(some_file, output_file_name)

            stripped_file = os.path.join(TMPDIR, output_file_base_name)
            strip_drm_or_copy_original(output_file_name, stripped_file)
            output_next_folder = args.dest_folder_for_winword if check_pdf_has_text(stripped_file) else args.dest_folder_for_ocr
            output_next_file = os.path.join(output_next_folder, output_file_base_name)
            print ("rename stripped file " + stripped_file + " to " + output_next_file)
            shutil.move(stripped_file, output_next_file)
            processed_files[sha256hash] = some_file
        except Exception as e:
            print (e)
