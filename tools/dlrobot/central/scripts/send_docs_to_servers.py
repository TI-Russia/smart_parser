from common.logging_wrapper import setup_logging
from dlrobot.dlrobot_server.send_docs import TDeclarationSender

import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("folders",  nargs="+")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    logger = setup_logging("send_docs")
    decl_sender = TDeclarationSender(logger, True, True)
    for d in args.folders:
        logger.info("folder = {}".format(d))
        result_folder =  os.path.join(d, "result")
        if not os.path.exists(result_folder):
            logger.error("no directory {} found".format(result_folder))
        else:
            decl_sender.send_declaraion_files_to_other_servers(d)


if __name__ == "__main__":
    main()