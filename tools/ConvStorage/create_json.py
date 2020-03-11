import glob
import os
import argparse
import hashlib
import json 
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob-pattern", dest='glob_pattern', default='./files/*.docx')
    parser.add_argument("--output-json", dest='output_file', default="converted_file_storage.json")
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    docx_files = glob.glob(args.glob_pattern)

    print("found {0} docx files".format(len(docx_files)))
    files = {}
    for docxfile in docx_files:
        pdffile = docxfile[:-len(".docx")]
        if not os.path.exists(pdffile):
            print ("cannot find  {} for {}".format(pdffile, docxfile))
            continue
        sha256hash = ""
        filesize = os.path.getsize(pdffile)

        with open(pdffile,"rb") as f:
            sha256hash = hashlib.sha256(f.read()).hexdigest();

        if sha256hash in files:
            if  files[sha256hash]['input_filesize'] != filesize:
                    print("Error! Collision found");
                    exit(1)
        files[sha256hash] = {
                'input_filesize': filesize,
                'converted': docxfile,
                'input' : pdffile                
        }
    with open(args.output_file, "w") as out:
        json.dump(files, out, indent=4)
            