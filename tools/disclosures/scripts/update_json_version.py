import json
import argparse
from declarations.input_json import TSourceDocument, TDeclaratorReference, TDlrobotHumanFile, TWebReference


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)
    parser.add_argument("--input-json", dest='input_json', required=True)
    parser.add_argument("--output-json", dest='output_json', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    with open(args.input_json, "r") as inp:
        input_dlrobot_human = json.load(inp)

    dlrobot_human = TDlrobotHumanFile()
    dlrobot_human.document_folder = input_dlrobot_human.get('r:folder', "domains")
    cnt = 0
    for web_site, web_site_info in input_dlrobot_human["files"].items():
        for sha256, file_info in web_site_info.items():
            path = file_info.get('r:path', file_info.get("dlrobot_path"))
            assert path
            if sha256 in dlrobot_human.document_collection:
                src_doc = dlrobot_human.document_collection[sha256]
            else:
                src_doc = TSourceDocument()
                dlrobot_human.document_collection[sha256] = src_doc
                src_doc.intersection_status = file_info.get('intersection_status')
                src_doc.document_path = path

            web_ref = TWebReference()
            web_ref.crawl_epoch = args.crawl_epoch
            web_ref.url = file_info.get('r:url')
            src_doc.references.append(web_ref)

            if 'd:office_id' in file_info:
                decl_rec = TDeclaratorReference()
                decl_rec.file_path = file_info.get('d:path')
                decl_rec.office_id = file_info.get('d:office_id')
                decl_rec.income_year = file_info.get('d:income_year')
                decl_rec.document_id = file_info.get('d:document_id')
                decl_rec.document_file_id = file_info.get('d:document_file_id')
                decl_rec.document_file_url = file_info.get('d:media_url')
                src_doc.references.append(decl_rec)



    dlrobot_human.write(args.output_file)
