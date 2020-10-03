import argparse
import os
import shutil
import psutil
import time
from common_server_worker import PITSTOP_FILE, TYandexCloud


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud",  dest='cloud', default=False, action="store_true",
                        required=False)

    parser.add_argument("--smart-parser-folder",  dest='smart_parser_folder', default='/home/sokirko/smart_parser',
                        required=False)
    args = parser.parse_args()
    return args


def git_pull(path):
    cmd = "git -C {} pull".format(path)
    exit_code = os.system(cmd)
    if exit_code != 0:
        print ("cannot git pull")
        raise Exception(cmd + " failed")


def kill_firefox():
    os.system("pkill -f firefox")
    os.system("pkill -f geckodriver")
    os.system("pkill -f dlrobot.py")


def stop_dlrobot_worker():
    with open(os.path.join("/tmp/dlrobot_worker/", PITSTOP_FILE), "w") as outp:
        pass
    start_time = time.time()
    while True:
        still_active = False
        for proc in psutil.process_iter():
            cmdline = " ".join(proc.cmdline())
            if proc.pid != os.getpid():
                if 'dlrobot_worker.py' in cmdline:
                    still_active = True
        if not still_active:
            break
        if time.time() - start_time > 60*60:
            raise Exception ("cannot stop dlrobot_worker in one hour")
    kill_firefox()


def start_dlrobot_worker():
    os.system('sudo systemctl start dlrobot_worker')


def check_free_disk_space():
    total, used, free = shutil.disk_usage('/tmp')
    if free < 2**30:
        raise Exception("at least 1GB free disk space must be available")


def get_hosts():
    for m in TYandexCloud.list_instances():
        cloud_id = m['id']
        if m['status'] == 'STOPPED':
            TYandexCloud.start_yandex_cloud_worker(cloud_id)
        yield TYandexCloud.get_worker_ip(m)
    yield "avito"
    yield "lena"


def update_one_worker_on_the_worker():
    stop_dlrobot_worker()
    check_free_disk_space()
    git_pull(args.smart_parser_folder)
    start_dlrobot_worker()
    print("initalize success")


def update_cloud_from_central():
    script = os.path.realpath(__file__)
    updaters = list()
    for host in get_hosts():
        proc = subprocess.Popen(
            ['ssh',
              host,
             "python3",
             script,
             ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        updaters.append(proc)

    for p in updaters:
        exit_code = p.wait(60*60)
        if exit_code != 0:
            raise Exception("cannot update cloud")


if __name__ == "__main__":
    args = parse_args()
    if args.cloud:
        update_cloud_from_central()
    else:
        update_one_worker_on_the_worker()