import argparse
from ConvStorage.conv_storage_server import TConvertStorage
import logging

def setup_logging():
    logger = logging.getLogger("add_database")
    logger.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler("convert_pdf.log", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-database", dest='main_db', required=True)
    parser.add_argument("--add-database", dest='add_db', required=True)
    parser.add_argument("--move", dest='move', action="store_true", default=False, required=False)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logger = setup_logging()
    main_db = TConvertStorage(logger, args.main_db)
    add_db = TConvertStorage(logger, args.add_db)
    main_db.add_database(add_db, args.move)
    main_db.save_database()

