import glob
import os
import argparse
import hashlib
import json 
from shutil import copyfile
TMPDIR = "tmp"
assert os.path.exists(TMPDIR)

# rm nohup.out; nohup python3 copy_new.py --input-glob-pattern 'out.documentfile/*.pdf' --old-json converted_file_storage.json  --dest-folder pdf  --dest-folder-for-ocr pdf.ocr --dest-folder-for-winword pdf.winword &

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob-pattern", dest='glob_pattern', default='./files/*.pdf')
    parser.add_argument("--old-json", dest='old_json')
    parser.add_argument("--dest-folder", dest='dest_folder')
    parser.add_argument("--dest-folder-for-ocr", dest='dest_folder_for_ocr')
    parser.add_argument("--dest-folder-for-winword", dest='dest_folder_for_winword')
    return parser.parse_args()


def check_pdf_has_text(filename):
    cmd = "pdftotext {0} dummy.txt".format(filename)
    print (cmd )
    os.system(cmd)
    return os.path.getsize("dummy.txt") > 200


def strip_drm(filename, stripped_file):
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
        return True
    return False


def copyfile_to_folder(filename, folder):
    outfilename = os.path.join(folder, os.path.basename(filename))
    print ("copy " +filename + " to " + outfilename)
    copyfile (filename, outfilename)


if __name__ == '__main__':
    args = parse_args()
    all_files = glob.glob(args.glob_pattern)
    old_json = {}
    if args.old_json is not None: 
        with open(args.old_json, "r", encoding="utf8") as inp:
            old_json = json.load(inp)

    print("found {0} input files".format(len(all_files)))
    files = {}
    for somefile in  all_files:
        sha256hash = ""
        with open(somefile,"rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest();
        
        if sha256hash not in files:
            if sha256hash not in old_json:
                copyfile_to_folder (somefile, args.dest_folder)
            
                stripped_file = os.path.join(TMPDIR, os.path.basename(somefile))
                if not strip_drm(somefile, stripped_file):
                    stripped_file = somefile
                        
                if check_pdf_has_text(stripped_file):
                    copyfile_to_folder (stripped_file, args.dest_folder_for_winword)
                else:
                    copyfile_to_folder (stripped_file, args.dest_folder_for_ocr)
            else:
                print ("skip " +somefile + " (already)")

        files[sha256hash] = somefile
            