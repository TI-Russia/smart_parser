from declarations.input_json import TSourceDocument, TDlrobotHumanFile
import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="can be stats, select, print_sha256, print_web_sites, delete")
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file', required=False)
    parser.add_argument("--sha256-list-file", dest='sha256_list_file', required=False)
    return parser.parse_args()


def print_web_sites(dlrobot_human):
    value: TSourceDocument
    for key, value in dlrobot_human.document_collection.items():
        print("{}\t{}".format(key, value.get_web_site()))


def read_sha256_list(filename):
    sha_set = set()
    with open (filename) as inp:
        for x in inp:
            sha_set.add(x.strip())
    return sha_set


def select_or_delete_by_sha256(dlrobot_human, sha256_list, output_file, select=True):
    new_dlrobot_human = TDlrobotHumanFile(output_file, read_db=False, document_folder=dlrobot_human.document_folder)

    for sha256, src_doc in dlrobot_human.document_collection.items():
        if (sha256 in sha256_list) == (select):
            new_dlrobot_human.add_source_document(sha256, src_doc)

    new_dlrobot_human.write()


def main():
    args = parse_args()
    dlrobot_human = TDlrobotHumanFile(args.input_file)
    if args.action == "print_web_sites":
        print_web_sites(dlrobot_human)
    elif args.action == "stats":
        print(json.dumps(dlrobot_human.get_stats(), indent=4))
    elif args.action == "select" or args.action == "delete":
        sha_list = read_sha256_list(args.sha256_list_file)
        assert args.output_file is not None
        select_or_delete_by_sha256(dlrobot_human, sha_list, args.output_file, args.action == "select")
    else:
        raise Exception("unknown action")


if __name__ == '__main__':
    main()


