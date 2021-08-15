import os
from scp import SCPClient
import paramiko
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", dest='action', help="to_remote or from_remote")
    parser.add_argument("--file", dest='basename_files', required=True, nargs='+')
    parser.add_argument("--remote-host", dest='remote_host', default="195.70.213.239")
    parser.add_argument("--username", dest='username', default="sokirko")
    parser.add_argument("--remote-host-folder", dest='remote_host_folder',
                        default=".")
    parser.add_argument("--local-folder", dest='local_folder',
                        default=".")
    return parser.parse_args()


class TCopier:
    def __init__(self, args):
        self.args = args
        assert (os.environ.get("password_remote_host") is not None)
        self.remote_password = os.environ["password_remote_host"]

    def get_files(self):
        for l in self.args.basename_files:
            local_file = os.path.join(self.args.local_folder, l)
            remote_file = os.path.join(self.args.remote_host_folder, l)
            yield local_file, remote_file

    def create_ssh(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.args.remote_host, 22, self.args.username, self.remote_password)
        return client

    def get_file_from_remote_host(self):
        ssh = self.create_ssh()

        for local_file, remote_file in self.get_files():
            if os.path.exists(local_file):
                print("rm " + local_file)
                os.unlink(local_file)

            with SCPClient(ssh.get_transport()) as scp:
                scp.get(remote_path=remote_file, local_path=local_file)
            print("read file  {} from remote host".format(local_file))

    def put_file_to_remote_host(self):
        ssh = self.create_ssh()

        for local_file, remote_file in self.get_files():
            with SCPClient(ssh.get_transport()) as scp:
                scp.put(local_file, remote_path=remote_file)

            print("save {} to remote host".format(local_file))


if __name__ == '__main__':
    args = parse_args()
    copier = TCopier(args)
    if args.action == "from_remote":
        copier.get_file_from_remote_host()
    elif args.action == "to_remote":
        copier.put_file_to_remote_host()
