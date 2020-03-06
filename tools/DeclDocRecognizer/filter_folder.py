import argparse
import json
import re
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", dest='folder')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    files = [ f for f in os.listdir(args.folder) if f.endswith(".json") ]
    print ("found {} files in {}".format(len(files), args.folder))
    for x in files:
        jsonfile = os.path.join(args.folder, x)
        with open (jsonfile, "r", encoding="utf-8") as inpf:
            try:
                if json.load(inpf).get('result') == "some_other_document_result":
                    filename = jsonfile[:-len(".json")]
                    if os.path.exists(filename):
                        print("remove    file {}".format(filename))
                        os.unlink(filename)
                    else:
                        print ("cannot find file {}".format(filename))
            except Exception as e:
                print ("cannot open json {}: {}".format(jsonfile, e))
        os.unlink(jsonfile)