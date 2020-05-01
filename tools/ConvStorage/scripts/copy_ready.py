import glob
import os
import shutil
import argparse

def copyfile_to_folder(filename, folder):
    outfilename = os.path.join(folder, os.path.basename(filename))
    if not os.path.exists(outfilename):
        print ("copy " +filename + " to " + outfilename)
        shutil.copyfile (filename, outfilename)
    else:
        print ("skip copying " +filename + " (already exists)")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob-pattern", dest='glob_pattern', default='./pdf/*.pdf')
    parser.add_argument("--dest-folder", dest='dest_folder', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    for pdf in glob.glob(args.glob_pattern):
        docx = pdf + ".docx"
        if os.path.exists(docx):
            copyfile_to_folder(pdf, args.dest_folder)
            copyfile_to_folder(docx, args.dest_folder)
