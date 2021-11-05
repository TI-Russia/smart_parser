from common.russian_regions import TRussianRegions
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", dest='input_file')
    parser.add_argument("--output-file", dest='output_file')
    return parser.parse_args()


def main():
    args = parse_args()
    regions = TRussianRegions()
    with open(args.input_file) as inp:
        for l in inp:
            office_id, name = l.strip().split("\t")
            region = regions.get_region_in_nominative(name)
            region_id = str(-1) if region is None else str(region.id)
            print("\t".join([office_id, name, region_id]))


if __name__ == "__main__":
    main()