import argparse
import os
import shutil
import psutil
import time
from common_server_worker import PITSTOP_FILE, TYandexCloud
import subprocess

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud",  dest='cloud', default=False, action="store_true",
                        required=False)
    parser.add_argument("--host",  dest='host', default=None,  required=False)

    parser.add_argument("--smart-parser-folder",  dest='smart_parser_folder', default='/home/sokirko/smart_parser',
                        required=False)
    parser.add_argument("--break-crawling",  dest='break_crawling', default=False,  required=False, action="store_true")
    args = parser.parse_args()
    return args


def git_pull(path):
    cmd = "git -C {} pull".format(path)
    exit_code = os.system(cmd)
    if exit_code != 0:
        print ("cannot git pull")
        raise Exception(cmd + " failed")


def kill_crawling():
    os.system("pkill -f firefox")
    os.system("pkill -f geckodriver")
    os.system("pkill -f dlrobot.py")


def stop_dlrobot_worker_gently():
    pitstop_file = os.path.join("/tmp/dlrobot_worker/", PITSTOP_FILE)
    with open(pitstop_file, "w") as outp:
        pass
    assert os.path.exists(pitstop_file)
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
    kill_crawling()


def stop_dlrobot_worker_with_losses():
    kill_crawling()
    os.system('sudo systemctl stop dlrobot_worker')


def start_dlrobot_worker():
    os.system('sudo systemctl start dlrobot_worker')


def check_free_disk_space():
    total, used, free = shutil.disk_usage('/tmp')
    if free < 2**30:
        raise Exception("at least 1GB free disk space must be available")


def get_hosts(args):
    if args.host is not None:
        yield (args.host, args.host)
        return

    for m in TYandexCloud.list_instances():
        cloud_id = m['id']
        if m['status'] == 'STOPPED':
            TYandexCloud.start_yandex_cloud_worker(cloud_id)
        yield (TYandexCloud.get_worker_ip(m), m['name'])
    yield ("avito", "avito")
    yield ("lena", "lena")


def update_one_worker_on_the_worker(args):
    if args.break_crawling:
        stop_dlrobot_worker_with_losses()
    else:
        stop_dlrobot_worker_gently()
    check_free_disk_space()
    git_pull(args.smart_parser_folder)
    start_dlrobot_worker()
    print("initalize success")


def update_cloud_from_central(args):
    script = os.path.realpath(__file__)
    updaters = list()
    for host, name in get_hosts(args):
        print ("update {}".format(name))
        cmd_args =['ssh',
              '-o',  "StrictHostKeyChecking no",
              host,
              "python3",
               script
             ]
        if args.break_crawling:
            cmd_args.append("--break-crawling")
        print(" ".join(cmd_args))
        proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        updaters.append(proc)

    for p in updaters:
        exit_code = p.wait(60*60)
        print(p.communicate(timeout=10))
        if exit_code != 0:
            raise Exception("cannot update cloud")


if __name__ == "__main__":
    args = parse_args()
    if args.cloud or args.host is not None:
        update_cloud_from_central(args)
    else:
        update_one_worker_on_the_worker(args)