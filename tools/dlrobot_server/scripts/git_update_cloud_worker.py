import argparse
import os
import shutil
import psutil
import time
import sys
sys.path.append(os.path.join( os.path.dirname(__file__), '..'))
from common_server_worker import PITSTOP_FILE, TYandexCloud
import subprocess


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud",  dest='cloud', default=False, action="store_true",
                        required=False)
    parser.add_argument("--action",  dest='action', default="restart", help="can be start, stop or restart, only_git_pull")
    parser.add_argument("--host",  dest='host', default=None,  required=False)

    parser.add_argument("--smart-parser-folder",  dest='smart_parser_folder', default='/home/sokirko/smart_parser',
                        required=False)
    parser.add_argument("--break-crawling",  dest='break_crawling', default=False,  required=False, action="store_true")
    args = parser.parse_args()
    return args


def kill_crawling():
    os.system("pkill -f firefox")
    os.system("pkill -f chrome")
    os.system("pkill -f geckodriver")
    os.system("pkill -f chromedriver")
    os.system("pkill -f dlrobot.py")


def stop_dlrobot_worker_gently():
    worker_folder = "/tmp/dlrobot_worker"
    if not os.path.exists(worker_folder):
        print("no dlrobot_worker folder found: {}".format(worker_folder))
        return
    pitstop_file = os.path.join(worker_folder, PITSTOP_FILE)
    with open(pitstop_file, "w") as outp:
        pass
    assert os.path.exists(pitstop_file)
    start_time = time.time()
    while True:
        time.sleep(60)
        still_active = False
        for proc in psutil.process_iter():
            try:
                cmdline = " ".join(proc.cmdline())
                if proc.pid != os.getpid():
                    if 'dlrobot_worker.py' in cmdline:
                        still_active = True
            except Exception as exp:
                continue
        if not still_active:
            break
        if time.time() - start_time > 4*60*60:
            raise Exception ("cannot stop dlrobot_worker in 4 hours")
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
    yield ("samsung", "samsung")


def update_one_worker_on_the_worker(args):
    if args.action == "restart" or args.action == "stop":
        if args.break_crawling:
            stop_dlrobot_worker_with_losses()
        else:
            stop_dlrobot_worker_gently()

    check_free_disk_space()

    if args.action == "restart" or args.action == "start":
        start_dlrobot_worker()


def ssh_command(host, cmd_args):
    cmd_args = ['ssh',
                '-o', "StrictHostKeyChecking no",
                host,
                ] + cmd_args
    print(" ".join(cmd_args))
    return subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def update_cloud_from_central(args):
    hosts = list(get_hosts(args))
    for host, name in hosts:
        if os.system("ping -c 1 {}".format(host)) != 0:
            raise Exception("cannot ping host {}".format(host))

    for host, name in hosts:
        proc = ssh_command (host, ["git", "-C", args.smart_parser_folder,  "pull"])
        proc.wait(600)
        if proc.returncode != 0:
            raise Exception("cannot update git on host {}".format(name))
    if args.action == "only_git_pull":
        return

    updaters = list()
    for host, name in hosts:
        cmd_args = ["python3", os.path.realpath(__file__)]
        if args.break_crawling:
            cmd_args.append("--break-crawling")
        if args.action != "restart":
            cmd_args.extend(['--action', args.action])
        proc = ssh_command (host, cmd_args)
        updaters.append(proc)

    for p in updaters:
        p.wait(5*60*60)
        print(p.communicate(timeout=10))
        if p.returncode != 0:
            raise Exception("cannot update, failed command: {}".format(p.args))


if __name__ == "__main__":
    args = parse_args()
    if args.cloud or args.host is not None:
        update_cloud_from_central(args)
    else:
        update_one_worker_on_the_worker(args)