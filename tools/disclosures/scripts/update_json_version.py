from declarations.input_json import TSourceDocument, TDeclaratorReference, TDlrobotHumanFile, TWebReference, TIntersectionStatus

import json
import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crawl-epoch", dest='crawl_epoch', type=int, required=True)
    parser.add_argument("--input-json", dest='input_json', required=True)
    parser.add_argument("--human-file-format", dest='human_file_format', action="store_true", default=False)
    parser.add_argument("--output-json", dest='output_json', required=True)
    return parser.parse_args()


def get_files(args, json_body):
    if args.human_file_format:
        for sha256, file_info in json_body['files'].items():
            yield None, sha256, file_info
    elif 'files' in json_body:
        for web_site, web_site_info in json_body["files"].items():
            for sha256, file_info in web_site_info.items():
                yield web_site, sha256, file_info
    else:
        for web_site, web_site_info in json_body.items():
            for sha256, file_info in web_site_info.items():
                yield web_site, a256, file_info


if __name__ == '__main__':
    args = parse_args()
    with open(args.input_json, "r") as inp:
        input_dlrobot_human = json.load(inp)

    dlrobot_human = TDlrobotHumanFile()
    dlrobot_human.document_folder = input_dlrobot_human.get('r:folder', "domains")
    if args.human_file_format:
        dlrobot_human.document_folder = input_dlrobot_human.get('d:folder')
    cnt = 0
    domain_to_office = dict()
    for office_id, d_list in input_dlrobot_human.get("office_to_domains", dict()).items():
        for d in d_list:
            domain_to_office[d] = int(office_id)

    for website, sha256, file_info in get_files(args, input_dlrobot_human):
        if args.human_file_format:
            path = file_info.get('d:path')
        else:
            path = file_info.get('r:path', file_info.get("dlrobot_path"))
        if website is not None and os.path.basename(path) == path:
            path = os.path.join(website, path)
        assert path
        if sha256 in dlrobot_human.document_collection:
            src_doc = dlrobot_human.document_collection[sha256]
        else:
            src_doc = TSourceDocument()
            dlrobot_human.document_collection[sha256] = src_doc
            src_doc.intersection_status = file_info.get('intersection_status')
            if src_doc.intersection_status is None and args.human_file_format:
                src_doc.intersection_status = TIntersectionStatus.only_human
            src_doc.document_path = path
        if not args.human_file_format:
            web_ref = TWebReference()
            web_ref.crawl_epoch = args.crawl_epoch
            web_ref.url = file_info.get('r:url', website)
            src_doc.add_web_reference(web_ref)

        if 'd:office_id' in file_info:
            decl_rec = TDeclaratorReference()
            decl_rec.office_id = file_info.get('d:office_id')
            decl_rec.income_year = file_info.get('d:income_year')
            decl_rec.document_id = file_info.get('d:document_id')
            decl_rec.document_file_id = file_info.get('d:document_file_id')
            decl_rec.document_file_url = file_info.get('d:media_url')
            decl_rec.web_domain = file_info.get('d:domain', website)
            src_doc.calculated_office_id = file_info.get('d:office_id')
            src_doc.add_decl_reference(decl_rec)

        if src_doc.calculated_office_id is None and website is not None:
            src_doc.calculated_office_id = domain_to_office.get(website)



    dlrobot_human.write(args.output_json)
