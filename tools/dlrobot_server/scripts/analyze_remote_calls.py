from dlrobot_server.remote_call import TRemoteDlrobotCall
from common.logging_wrapper import setup_logging
from disclosures_site.declarations.web_sites import TDeclarationWebSites, TWebSiteReachStatus
from common.html_parser import THtmlParser

import os
import subprocess
import argparse
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file",  dest='input_file')
    parser.add_argument("--output-file",  dest='output_file')
    parser.add_argument("--action",  dest='action', help="can be print_sites_wo_results")
    args = parser.parse_args()
    return args


def get_html_title_from_url(url):
    try:
        with subprocess.Popen(['curl', '-L', '-m', '20', url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
            data = proc.stdout.read()
            html_title = THtmlParser(data).page_title
            if html_title is not None and html_title.strip() != "":
                return html_title.replace("\n", " ").strip()
    except Exception as ex:
        #print (ex)
        pass
    return "unknown_title"


def print_sites_wo_results(logger, remote_calls, web_sites, output_file):
    good = set()
    bad = set()
    statuses = defaultdict(set)
    for r in remote_calls:
        url, _ = os.path.splitext(r.project_file)
        statuses[url].add(r.reach_status if r.reach_status is not None else "null")
        if r.result_files_count > 0:
            good.add(url)
        else:
            bad.add(url)

    cnt = 0
    for url in bad:
        if url in good:
            continue
        cnt += 1
        if web_sites.has_web_site(url) and TWebSiteReachStatus.can_communicate (web_sites.get_web_site(url).reach_status):
            logger.info ("browse {} ...".format(url))
            title = get_html_title_from_url(url)
            output_file.write("{}\t{}\t{}\n".format(
                url,
                ",".join(statuses.get(url, ["unk"])),
                title)
            )
        #if cnt > 10:
        #    break


if __name__ == "__main__":
    args = parse_args()
    logger = setup_logging("analyze_remote_calls")
    web_sites = TDeclarationWebSites(logger)
    web_sites.load_from_disk()
    remote_calls = TRemoteDlrobotCall.read_remote_calls_from_file(args.input_file)
    with open(args.output_file, "w") as outp:
        if args.action == "print_sites_wo_results":
            print_sites_wo_results(logger, remote_calls, web_sites, outp)
        else:
            raise Exception('unknown acton')