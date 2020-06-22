import argparse
from ConvStorage.conv_storage_server import TConvertStorage
import logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-database", dest='main_db', required=True)
    parser.add_argument("--add-database", dest='add_db', required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = logging.getLogger("add_database")
    main_db = TConvertStorage(logger, args.main_db)
    add_db = TConvertStorage(logger, args.add_db)
    main_db.add_database(add_db)
    main_db.save_database()

