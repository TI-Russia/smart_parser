import logging

def close_logger(logger):
    for i in logger.handlers:
        logger.removeHandler(i)
        i.flush()
        i.close()
