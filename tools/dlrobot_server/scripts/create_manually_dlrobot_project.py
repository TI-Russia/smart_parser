from common.logging_wrapper import setup_logging
from  web_site_db.robot_project import TRobotProject
from dlrobot_server.send_docs import TDeclarationSender

import os
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--website", dest="website", required=True)
    parser.add_argument("--time-postfix", dest="time_postfix", default='111', required=False)
    parser.add_argument("--central-folder", dest="central_folder", required=True, help="~/declarator_hdd/declarator/dlrobot_central/processed_projects")
    parser.add_argument("files",  nargs="+")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    logger = setup_logging("create_manually")
    for f in args.files:
        assert os.path.exists(f)
    folder = os.path.join(args.central_folder, args.website + "." + args.time_postfix)
    if os.path.exists(folder):
        raise Exception("folder {} exists".format(folder))
    os.mkdir(folder)
    TRobotProject.create_project_from_exported_files(logger, args.website, args.files, project_folder=folder)
    decl_sender = TDeclarationSender(logger, True, True)
    decl_sender.send_declaraion_files_to_other_servers(folder)


if __name__ == "__main__":
    main()
