from declarations.serializers import TDlrobotHumanFile
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", dest='input_json', default="dlrobot_human.json", required=True)
    parser.add_argument("--sha-256", dest='shas', action="append", required=True)
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human_subset.json", required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    dlrobot_human = TDlrobotHumanFile(input_file_name=args.input_json)
    new_dlrobot_human = TDlrobotHumanFile()
    new_dlrobot_human.document_folder = dlrobot_human.document_folder

    for sha256, src_doc in dlrobot_human.document_collection.items():
        if sha256 in args.shas:
            new_dlrobot_human.add_source_document(sha256, src_doc)

    new_dlrobot_human.write(args.output_json)
