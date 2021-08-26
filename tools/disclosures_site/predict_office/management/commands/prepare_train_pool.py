from disclosures_site.predict_office.office_pool import TOfficePool
from common.logging_wrapper import setup_logging
import random
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", dest='pool', nargs="+", required=True)
    parser.add_argument("--output-train-pool", dest='output_train_pool')
    parser.add_argument("--row-count", dest='row_count', required=False, type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logging(log_file_name="prepare_train.log")
    output_pool = TOfficePool(logger)
    for pool_path in args.pool:
        if pool_path.find(',') != -1:
            pool_path, repeat_count = pool_path.split(",")
            repeat_count = int(repeat_count)
        else:
            repeat_count = 1
        logger.info("read pool {}".format(pool_path))
        pool = TOfficePool(logger)
        pool.read_cases(pool_path, make_uniq=True)
        if repeat_count > 1:
            logger.info("add it {} times".format(repeat_count))
        for i in range(repeat_count):
            output_pool.pool.extend(pool.pool)

    random.shuffle(output_pool.pool)
    if args.row_count is not None:
        output_pool.pool = output_pool.pool[0:args.row_count]

    TOfficePool.write_pool(output_pool.pool, args.output_train_pool)


if __name__ == "__main__":
    main()