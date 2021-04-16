import logging
import os


def setup_logging(logger_name=None, log_file_name=None, append_mode=False):
    if logger_name is None:
        if log_file_name is not None:
            logger_name,_ = os.path.splitext(log_file_name)
        else:
            logger_name = "logger"
    elif log_file_name is None:
        log_file_name = logger_name + ".log"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create file handler which logs even debug messages
    if log_file_name is not None:
        if append_mode:
            fh = logging.FileHandler(log_file_name, "a+", encoding="utf8")
        else:
            if os.path.exists(log_file_name):
                os.remove(log_file_name)
            fh = logging.FileHandler(log_file_name, encoding="utf8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    return logger


def close_logger(logger):
    for i in logger.handlers:
        logger.removeHandler(i)
        i.flush()
        i.close()
