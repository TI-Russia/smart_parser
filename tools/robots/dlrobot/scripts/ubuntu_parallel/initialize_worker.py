import argparse
import sys
import os
import shutil

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--declarator-hdd-folder",  dest='declarator_hdd_folder', required=True)
    parser.add_argument("--smart-parser-folder",  dest='smart_parser_folder', default='/home/sokirko/smart_parser',
                        required=False)

    args = parser.parse_args()
    return args



def setup_declarator_hdd(declarator_hdd_folder):
    if not os.path.exists(declarator_hdd_folder):
        os.mkdir(declarator_hdd_folder)
    if len(os.listdir(declarator_hdd_folder)) == 0:
        cmd = "sshfs migalka:/mnt/sdb {}".format(declarator_hdd_folder)
        exit_code = os.system (cmd)
        if exit_code != 0:
            raise Exception(cmd + " failed")


def kill_firefox():
    os.system("pkill -f firefox")
    os.system("pkill -f geckodriver")
    os.system("pkill -f dlrobot")


def check_dlrobot_path(path):
    if not os.path.exists(path):
        raise Exception("cannot find {}".format(dlrobot_path))


def check_free_disk_space():
    total, used, free = shutil.disk_usage(os.path.dirname(__file__))
    if free < 2**30:
        raise Exception("at least 1GB free disk space must be available")


def git_pull(path):
    cmd = "git -C {} pull".format(path)
    exit_code = os.system(cmd)
    if exit_code != 0:
        raise Exception(cmd + " failed")


if __name__ == "__main__":
    args = parse_args()
    git_folder = '/home/sokirko/smart_parser'
    setup_declarator_hdd(args.declarator_hdd_folder)
    kill_firefox()
    check_dlrobot_path(args.smart_parser_folder)
    check_free_disk_space()
    git_pull(args.smart_parser_folder)
    print("intalize success")
