
from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory, TOfficeInMemory
from office_db.declaration_office_website import TDeclarationWebSite, TWebSiteReachStatus
from web_site_db.web_sites import TDeclarationWebSiteList, TDeclarationWebSiteObsolete

import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging("set_rubrics")
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()
    for o in offices.offices.values():
        o.rubric_id = offices.build_office_rubric(logger, o.office_id)
    logger.info("write to {}".format(args.output_file))
    offices.write_to_local_file(args.output_file)


if __name__ == "__main__":
    main()