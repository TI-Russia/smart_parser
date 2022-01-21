from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory
from office_db.declaration_office_website import TDeclarationWebSite, TWebSiteReachStatus
from office_db.web_site_list import TDeclarationWebSiteList, TDeclarationWebSiteObsolete

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging("join_office_and_websites")
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()

    web_sites_db = TDeclarationWebSiteList(logger,
                                           TDeclarationWebSiteList.default_input_task_list_path).load_from_disk()
    url_info: TDeclarationWebSiteObsolete
    for url, url_info in web_sites_db.web_sites.items():
        office_id = url_info.calculated_office_id
        office: TOfficeInMemory
        office = offices.offices.get(int(office_id))
        if office is None:
            logger.debug("cannot find office_id={}, url={} no valid urls, deleted office?".format(office_id, url))
            continue
        p = url_info.http_protocol if url_info.http_protocol is not None else "http"
        i = TDeclarationWebSite()
        i.url = p + "://" + url
        i.reach_status = url_info.reach_status
        i.comments = url_info.comments
        i.redirect_to = url_info.redirect_to
        i.title = url_info.title
        office.office_web_sites.append(i)
    for o in offices.offices.values():
        o.office_web_sites.sort(key=lambda x: 1 if x.reach_status == TWebSiteReachStatus.normal else 0)
    logger.info("write to {}".format(args.output_file))
    offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()