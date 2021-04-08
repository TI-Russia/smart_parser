from common.file_storage import TFileStorage
from common.logging_wrapper import setup_logging
import sys

if __name__ == "__main__":
    logger = setup_logging(logger_name="print_all_keys")
    data_folder = sys.argv[1]
    logger.info("open folder {}".format(data_folder))
    file_storage = TFileStorage(logger, data_folder, read_only=True)
    for k in file_storage.get_all_keys():
        print(k)
    file_storage.close_file_storage()