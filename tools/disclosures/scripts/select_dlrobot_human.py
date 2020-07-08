from declarations.input_json_specification import dhjs
import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", dest='input_json', default="dlrobot_human.json", required=True)
    parser.add_argument("--sha-256", dest='shas', action="append", required=True)
    parser.add_argument("--output-json", dest='output_json', default="dlrobot_human_subset.json", required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    with open (args.input_json, "r") as inp:
        dlrobot_human = json.load(inp)

    dlrobot_human_new =  {
        dhjs.declarator_folder: dlrobot_human[dhjs.declarator_folder],
        dhjs.dlrobot_folder: dlrobot_human[dhjs.dlrobot_folder],
        dhjs.file_collection: dict(),
        dhjs.offices_to_domains: dlrobot_human[dhjs.offices_to_domains]
    }

    for web_site, web_site_info in dlrobot_human[dhjs.file_collection].items():
        for sha256, file_info in web_site_info.items():
            if sha256 in args.shas:
                if web_site not in dlrobot_human_new[dhjs.file_collection]:
                    dlrobot_human_new[dhjs.file_collection][web_site] = dict()
                dlrobot_human_new[dhjs.file_collection][web_site][sha256] = file_info

    with open (args.output_json, "w") as outp:
        json.dump(dlrobot_human_new, outp, indent=4)
