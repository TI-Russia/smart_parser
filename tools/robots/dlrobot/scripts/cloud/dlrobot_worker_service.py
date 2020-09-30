import argparse
import psutil
import os
import shutil
import sys
import subprocess

SCRIPT_PATH = os.path.dirname( os.path.realpath(__file__) )
TEMP_FOLDER = "/tmp"
WORKER_FOLDER_PREFIX = "dlrobot_worker"
WORKER_BASE_NAME = "dlrobot_worker.py"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-count", dest='worker_count', default=2, type=int)
    parser.add_argument("--home", dest='home', default="/home/sokirko", required=False,  help="home where smart_parser is installed")
    parser.add_argument(dest='action', help="can be start, stop, restart")
    args = parser.parse_args()
    return args


def start_worker(args, worker_id):
    os.putenv('ASPOSE_LIC', os.path.join(args.home, "lic.bin"))
    os.putenv('PYTHONPATH', os.path.join(args.home, "smart_parse/tools"))
    os.putenv('DECLARATOR_CONV_URL', "disclosures.ru:8091")
    os.putenv('DLROBOT_CENTRAL_SERVER_ADDRESS', "disclosures.ru:8089")

    path = os.path.join(TEMP_FOLDER, WORKER_FOLDER_PREFIX + str(worker_id))
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    worker_path = os.path.join(SCRIPT_PATH, WORKER_BASE_NAME)
    #os.spawnve(os.P_NOWAIT, '/usr/bin/python3', args, os.environ)-
    proc = subprocess.Popen(['/usr/bin/python3', worker_path, '--tmp-folder', '.',  '--run-forever'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=path
    )
    #proc.communicate(12)
    #os.system("cd {}; /usr/bin/python3 {} --tmp-folder . --run-forever &".format(path, worker_path))


def start(args):
    for proc in psutil.process_iter():
        cmdline = " ".join(proc.cmdline())
        if WORKER_BASE_NAME in cmdline:
            sys.stderr.write('process workers are still running, delete workers first\n')
            sys.exit(1)

    for p in range(args.worker_count):
        start_worker(args, p + 1)


def stop(args):
    for proc in psutil.process_iter():
        cmdline = " ".join(proc.cmdline())
        if WORKER_BASE_NAME in cmdline or 'firefox' in cmdline:
            proc.kill()


if __name__ == "__main__":
    args = parse_args()
    if args.action == "start":
        start(args)
    if args.action == "stop":
        stop(args)
    if args.action == "restart":
        stop(args)
        start(args)