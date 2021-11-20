from office_db.russian_regions import TRussianRegions
from common.logging_wrapper import setup_logging
from office_db.offices_in_memory import TOfficeTableInMemory

import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging("calc_region")
    regions = TRussianRegions()
    offices = TOfficeTableInMemory(use_office_types=False)
    offices.read_from_local_file()

    with open(args.input_file) as inp:
        for l in inp:
            office_id, name, yandex_info = l.strip().split("\t")
            address = json.loads(yandex_info).get('address', '')
            region_id = regions.calc_region_by_address(address)
            if region_id is None:
                logger.error("cannot recognize region for {}".format(address))
            else:
                office = offices.offices.get(int(office_id))
                logger.debug("office_id={}, change region_id={} to region_id={}".format(office_id, office.region_id, region_id))
                office.region_id = region_id
                office.address = address
            #print("\t".join([office_id, name, yandex_info, str(region_id)]))
    logger.info("write to {}".format(args.output_file))
    offices.write_to_local_file(args.output_file)

if __name__ == "__main__":
    main()