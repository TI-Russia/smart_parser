import argparse
import sys
import os
import shutil
import time
import platform


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-file",  dest='project_file',  required=True)
    parser.add_argument("--smart-parser-folder",  dest='smart_parser_folder', required=True)
    parser.add_argument("--result-folder", dest='result_folder', required=True)
    parser.add_argument("--crawling-timeout", dest='crawling_timeout',
                            default="3h",
                            help="crawling timeout in seconds (there is also conversion step after crawling)")
    args = parser.parse_args()
    try:
        if not os.path.exists(args.result_folder):
            os.mkdir(args.result_folder)
    finally:
        os.path.exists(args.result_folder)

    return args


if __name__ == "__main__":
    args = parse_args()
    print("process {}".format(args.project_file))
    basename_project_file = os.path.basename(args.project_file)
    base_folder, _ = os.path.splitext(basename_project_file)
    folder = os.path.join("tmp", base_folder)
    os.makedirs(folder, exist_ok=True)
    os.chdir(folder)
    shutil.move(args.project_file, basename_project_file)
    if not os.path.exists(basename_project_file):
        raise Exception("cannot copy {}".format(args.project_file))
    dlrobot = os.path.join(args.smart_parser_folder, "tools/robots/dlrobot/dlrobot.py")
    goal_file = basename_project_file + ".clicks.stats"
    cmd = "timeout 4h python3 {} --project {} --crawling-timeout {} --last-conversion-timeout 30m >dlrobot.out 2>dlrobot.err".format(
        dlrobot, basename_project_file, args.crawling_timeout)
    exit_code = os.system(cmd)

    if os.path.exists("cached"):
        shutil.rmtree("cached", ignore_errors=True)
    if exit_code == 0 and os.path.exists("geckodriver.log"):
        os.unlink("geckodriver.log")
    if not os.path.exists(goal_file):
        print("cannot find {}, dlrobot.py failed, delete result folder".format(goal_file))
        exit_code = 1
        shutil.rmtree("result", ignore_errors=True)
    os.chdir("..")
    output_folder = os.path.join(args.result_folder, base_folder)
    if os.path.exists(output_folder):
        output_folder += ".{}".format(int(time.time()))
    shutil.copytree(base_folder, output_folder)
    shutil.rmtree(base_folder, ignore_errors=True)
    print("exit with code={}, hostname={}".format(exit_code, platform.node()))
    sys.exit(exit_code)


